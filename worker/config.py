"""Environment-backed worker configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} is required by the meeting worker.")
    return value


@dataclass(frozen=True)
class WorkerSettings:
    api_token: str
    supabase_url: str
    supabase_service_role_key: str
    recordings_dir: Path
    browser_profile_dir: Path
    chrome_executable_path: str
    bot_name: str
    virtual_sink: str
    max_meeting_seconds: int
    empty_meeting_grace_seconds: int
    max_meetings_per_user_per_day: int
    purge_interval_seconds: int
    keep_recordings: bool

    @classmethod
    def from_env(cls) -> WorkerSettings:
        recordings_dir = Path(os.getenv("RECORDINGS_DIR", "recordings")).resolve()
        recordings_dir.mkdir(parents=True, exist_ok=True)
        browser_profile_dir = Path(
            os.getenv("BROWSER_PROFILE_DIR", "browser-profile")
        ).resolve()
        browser_profile_dir.mkdir(parents=True, exist_ok=True)
        return cls(
            api_token=_required("WORKER_API_TOKEN"),
            supabase_url=_required("SUPABASE_URL"),
            supabase_service_role_key=_required("SUPABASE_SERVICE_ROLE_KEY"),
            recordings_dir=recordings_dir,
            browser_profile_dir=browser_profile_dir,
            chrome_executable_path=os.getenv(
                "CHROME_EXECUTABLE_PATH", "/usr/bin/google-chrome-stable"
            ).strip(),
            bot_name=os.getenv("MEET_BOT_NAME", "VideoSage Assistant").strip(),
            virtual_sink=os.getenv("PULSE_SINK_NAME", "Virtual_Sink").strip(),
            max_meeting_seconds=int(os.getenv("MAX_MEETING_SECONDS", "21600")),
            empty_meeting_grace_seconds=int(
                os.getenv("EMPTY_MEETING_GRACE_SECONDS", "120")
            ),
            max_meetings_per_user_per_day=int(
                os.getenv("MAX_MEETINGS_PER_USER_PER_DAY", "3")
            ),
            purge_interval_seconds=int(os.getenv("PURGE_INTERVAL_SECONDS", "3600")),
            keep_recordings=os.getenv("KEEP_RECORDINGS", "false").lower()
            in {"1", "true", "yes"},
        )
