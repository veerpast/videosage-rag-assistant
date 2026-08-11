"""Persistence boundary for autonomous meeting runs."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from supabase import Client, create_client
from worker.config import WorkerSettings


class MeetingStore:
    def __init__(self, settings: WorkerSettings):
        self.client: Client = create_client(
            settings.supabase_url,
            settings.supabase_service_role_key,
        )

    def create(
        self,
        meeting_id: str,
        user_id: str,
        meeting_url: str,
        language: str,
        bot_name: str,
    ) -> dict[str, Any]:
        payload = {
            "id": meeting_id,
            "user_id": user_id,
            "meeting_url": meeting_url,
            "language": language,
            "bot_name": bot_name,
            "status": "queued",
            "consent_confirmed_at": _utc_now(),
        }
        result = self.client.table("meeting_runs").insert(payload).execute()
        return result.data[0]

    def get(self, meeting_id: str, user_id: str | None = None) -> dict[str, Any] | None:
        query = self.client.table("meeting_runs").select("*").eq("id", meeting_id)
        if user_id:
            query = query.eq("user_id", user_id)
        result = query.maybe_single().execute()
        return result.data

    def list_recent(self, user_id: str, limit: int = 20) -> list[dict[str, Any]]:
        fields = (
            "id,title,status,language,bot_name,summary,action_items,"
            "key_decisions,open_questions,error_message,"
            "created_at,started_at,ended_at"
        )
        result = (
            self.client.table("meeting_runs")
            .select(fields)
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data

    def verify_user(self, access_token: str) -> str:
        response = self.client.auth.get_user(access_token)
        if not response.user:
            raise ValueError("Invalid user session")
        return str(response.user.id)

    def list_active(self) -> list[dict[str, Any]]:
        result = (
            self.client.table("meeting_runs")
            .select("id,meeting_url,language")
            .in_("status", ["queued", "running"])
            .order("created_at")
            .execute()
        )
        return result.data

    def has_active_meeting(self, user_id: str) -> bool:
        result = (
            self.client.table("meeting_runs")
            .select("id", count="exact")
            .eq("user_id", user_id)
            .in_("status", ["queued", "running"])
            .limit(1)
            .execute()
        )
        return bool(result.data)

    def meetings_in_last_day(self, user_id: str) -> int:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        result = (
            self.client.table("meeting_runs")
            .select("id", count="exact", head=True)
            .eq("user_id", user_id)
            .gte("created_at", cutoff)
            .execute()
        )
        return result.count or 0

    def mark_queued(self, meeting_id: str) -> None:
        self._update(
            meeting_id,
            {"status": "queued", "started_at": None, "ended_at": None},
        )

    def mark_running(self, meeting_id: str) -> None:
        self._update(
            meeting_id,
            {"status": "running", "started_at": _utc_now()},
        )

    def mark_completed(self, meeting_id: str, result: dict[str, Any]) -> None:
        self._update(
            meeting_id,
            {
                "status": "completed",
                "title": result["title"],
                "transcript": result["transcript"],
                "summary": result["summary"],
                "action_items": result["action_items"],
                "key_decisions": result["key_decisions"],
                "open_questions": result["open_questions"],
                "ended_at": _utc_now(),
                "error_message": None,
            },
        )

    def mark_failed(self, meeting_id: str, error: str) -> None:
        self._update(
            meeting_id,
            {
                "status": "failed",
                "error_message": error[:4000],
                "ended_at": _utc_now(),
            },
        )

    def _update(self, meeting_id: str, payload: dict[str, Any]) -> None:
        (
            self.client.table("meeting_runs")
            .update(payload)
            .eq("id", meeting_id)
            .execute()
        )


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
