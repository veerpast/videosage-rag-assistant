"""Authenticated FastAPI webhook and sequential autonomous bot worker."""

from __future__ import annotations

import asyncio
import hmac
import logging
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, status
from pydantic import BaseModel, Field, field_validator

load_dotenv()

from worker.config import WorkerSettings
from worker.meet_bot import GoogleMeetBot
from worker.supabase_store import MeetingStore
from worker.validation import validate_google_meet_url

LOGGER = logging.getLogger("videosage.worker")


class MeetingRequest(BaseModel):
    meeting_url: str = Field(min_length=20, max_length=500)
    language: str = "english"
    consent_confirmed: bool
    retention_days: int = Field(default=7, ge=1, le=30)

    @field_validator("meeting_url")
    @classmethod
    def validate_meeting_url(cls, value: str) -> str:
        return validate_google_meet_url(value)

    @field_validator("language")
    @classmethod
    def validate_language(cls, value: str) -> str:
        normalized = value.lower().strip()
        if normalized not in {"english", "hinglish"}:
            raise ValueError("language must be english or hinglish")
        return normalized

    @field_validator("consent_confirmed")
    @classmethod
    def validate_consent(cls, value: bool) -> bool:
        if not value:
            raise ValueError("Participant recording consent must be confirmed")
        return value


class MeetingAccepted(BaseModel):
    id: str
    status: str


class MeetingList(BaseModel):
    items: list[dict]


@dataclass(frozen=True)
class MeetingJob:
    id: str
    meeting_url: str
    language: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = WorkerSettings.from_env()
    app.state.settings = settings
    app.state.store = MeetingStore(settings)
    app.state.queue = asyncio.Queue(maxsize=100)
    await asyncio.to_thread(app.state.store.purge_expired)
    for meeting in await asyncio.to_thread(app.state.store.list_active):
        await asyncio.to_thread(app.state.store.mark_queued, meeting["id"])
        app.state.queue.put_nowait(
            MeetingJob(meeting["id"], meeting["meeting_url"], meeting["language"])
        )
    consumer = asyncio.create_task(_consume_jobs(app))
    purger = asyncio.create_task(_purge_expired_jobs(app))
    yield
    consumer.cancel()
    purger.cancel()
    await asyncio.gather(consumer, purger, return_exceptions=True)


app = FastAPI(
    title="VideoSage Meeting Worker",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
)


def authorize(request: Request, authorization: str = Header(default="")) -> None:
    expected = f"Bearer {request.app.state.settings.api_token}"
    if not hmac.compare_digest(authorization, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized"
        )


async def authenticated_user(
    request: Request,
    x_user_token: str = Header(default="", alias="X-User-Token"),
) -> str:
    if not x_user_token:
        raise HTTPException(status_code=401, detail="User session is required")
    try:
        return await asyncio.to_thread(
            request.app.state.store.verify_user, x_user_token
        )
    except Exception as exc:
        raise HTTPException(
            status_code=401, detail="User session is invalid or expired"
        ) from exc


@app.get("/health")
async def health(request: Request) -> dict:
    return {
        "status": "ok",
        "queued_jobs": request.app.state.queue.qsize(),
    }


@app.post(
    "/v1/meetings",
    response_model=MeetingAccepted,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(authorize)],
)
async def enqueue_meeting(
    payload: MeetingRequest,
    request: Request,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    user_id: str = Depends(authenticated_user),
) -> MeetingAccepted:
    meeting_id = _meeting_id(idempotency_key)
    store: MeetingStore = request.app.state.store
    existing = await asyncio.to_thread(store.get, meeting_id, user_id)
    if existing:
        return MeetingAccepted(id=meeting_id, status=existing["status"])

    if await asyncio.to_thread(store.has_active_meeting, user_id):
        raise HTTPException(
            status_code=409,
            detail="You already have a queued or running meeting.",
        )

    meetings_today = await asyncio.to_thread(store.meetings_in_last_day, user_id)
    if meetings_today >= request.app.state.settings.max_meetings_per_user_per_day:
        raise HTTPException(
            status_code=429,
            detail="Daily free-tier meeting limit reached. Try again tomorrow.",
        )

    await asyncio.to_thread(
        store.create,
        meeting_id,
        user_id,
        payload.meeting_url,
        payload.language,
        request.app.state.settings.bot_name,
        payload.retention_days,
    )
    try:
        request.app.state.queue.put_nowait(
            MeetingJob(meeting_id, payload.meeting_url, payload.language)
        )
    except asyncio.QueueFull as exc:
        await asyncio.to_thread(store.mark_failed, meeting_id, "Worker queue is full")
        raise HTTPException(status_code=503, detail="Worker queue is full") from exc
    return MeetingAccepted(id=meeting_id, status="queued")


@app.get(
    "/v1/meetings",
    response_model=MeetingList,
    dependencies=[Depends(authorize)],
)
async def recent_meetings(
    request: Request,
    limit: int = Query(default=20, ge=1, le=100),
    user_id: str = Depends(authenticated_user),
) -> MeetingList:
    items = await asyncio.to_thread(request.app.state.store.list_recent, user_id, limit)
    return MeetingList(items=items)


@app.get(
    "/v1/meetings/{meeting_id}",
    dependencies=[Depends(authorize)],
)
async def meeting_detail(
    meeting_id: uuid.UUID,
    request: Request,
    user_id: str = Depends(authenticated_user),
) -> dict:
    meeting = await asyncio.to_thread(
        request.app.state.store.get, str(meeting_id), user_id
    )
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    meeting.pop("meeting_url", None)
    return meeting


@app.delete(
    "/v1/meetings/{meeting_id}",
    dependencies=[Depends(authorize)],
)
async def delete_meeting(
    meeting_id: uuid.UUID,
    request: Request,
    user_id: str = Depends(authenticated_user),
) -> dict[str, bool]:
    store: MeetingStore = request.app.state.store
    meeting = await asyncio.to_thread(store.get, str(meeting_id), user_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    if meeting["status"] in {"queued", "running"}:
        raise HTTPException(
            status_code=409,
            detail="Wait for the active meeting to finish before deleting it.",
        )
    await asyncio.to_thread(store.delete, str(meeting_id), user_id)
    return {"deleted": True}


async def _consume_jobs(app: FastAPI) -> None:
    while True:
        job: MeetingJob = await app.state.queue.get()
        try:
            await asyncio.to_thread(
                _process_job, app.state.settings, app.state.store, job
            )
        except Exception:
            LOGGER.exception("Unhandled worker error for meeting %s", job.id)
        finally:
            app.state.queue.task_done()


async def _purge_expired_jobs(app: FastAPI) -> None:
    while True:
        await asyncio.sleep(app.state.settings.purge_interval_seconds)
        try:
            await asyncio.to_thread(app.state.store.purge_expired)
        except Exception:
            LOGGER.exception("Automatic meeting-retention cleanup failed")


def _process_job(
    settings: WorkerSettings, store: MeetingStore, job: MeetingJob
) -> None:
    # Keep the analysis pipeline out of API startup. The small free-tier worker
    # only pays this memory cost after a meeting recording is ready.
    from main import run_pipeline

    recording_path = settings.recordings_dir / f"{job.id}.wav"
    store.mark_running(job.id)
    try:
        GoogleMeetBot(settings).record(job.meeting_url, recording_path)
        result = run_pipeline(
            str(recording_path),
            language=job.language,
            build_chat=False,
        )
        store.mark_completed(job.id, result)
    except Exception as exc:
        LOGGER.exception("Meeting %s failed", job.id)
        store.mark_failed(job.id, str(exc))
    finally:
        if not settings.keep_recordings:
            _cleanup_recording_artifacts(recording_path)


def _meeting_id(idempotency_key: str | None) -> str:
    if not idempotency_key:
        return str(uuid.uuid4())
    try:
        return str(uuid.UUID(idempotency_key))
    except ValueError as exc:
        raise HTTPException(
            status_code=400, detail="Idempotency-Key must be a UUID"
        ) from exc


def _cleanup_recording_artifacts(recording_path: Path) -> None:
    candidates = [recording_path]
    converted = recording_path.with_name(f"{recording_path.stem}_converted.wav")
    candidates.append(converted)
    candidates.extend(converted.parent.glob(f"{converted.name}_chunk_*.wav"))
    for path in candidates:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            LOGGER.warning("Could not delete recording artifact %s", path)
