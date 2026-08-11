"""HTTP client used by Streamlit to communicate with the Oracle worker."""

from __future__ import annotations

import os
import uuid
from typing import Any

import requests


class WorkerClientError(RuntimeError):
    """Raised when the remote meeting worker cannot satisfy a request."""


def _config() -> tuple[str, str]:
    base_url = os.getenv("WORKER_API_URL", "").strip().rstrip("/")
    token = os.getenv("WORKER_API_TOKEN", "").strip()
    if not base_url or not token:
        raise WorkerClientError(
            "Set WORKER_API_URL and WORKER_API_TOKEN to enable the Google Meet bot."
        )
    return base_url, token


def is_configured() -> bool:
    return bool(
        os.getenv("WORKER_API_URL", "").strip()
        and os.getenv("WORKER_API_TOKEN", "").strip()
    )


def _request(method: str, path: str, user_token: str, **kwargs: Any) -> Any:
    base_url, token = _config()
    headers = kwargs.pop("headers", {})
    headers["Authorization"] = f"Bearer {token}"
    headers["X-User-Token"] = user_token
    try:
        response = requests.request(
            method,
            f"{base_url}{path}",
            headers=headers,
            timeout=20,
            **kwargs,
        )
    except requests.RequestException as exc:
        raise WorkerClientError(f"Meeting worker is unavailable: {exc}") from exc

    if not response.ok:
        try:
            detail = response.json().get("detail", response.text)
        except ValueError:
            detail = response.text
        raise WorkerClientError(
            f"Meeting worker returned {response.status_code}: {detail}"
        )
    return response.json()


def submit_meeting(
    meeting_url: str,
    user_token: str,
    language: str = "english",
    consent_confirmed: bool = False,
) -> dict[str, Any]:
    return _request(
        "POST",
        "/v1/meetings",
        user_token,
        headers={"Idempotency-Key": str(uuid.uuid4())},
        json={
            "meeting_url": meeting_url,
            "language": language,
            "consent_confirmed": consent_confirmed,
        },
    )


def list_meetings(user_token: str, limit: int = 20) -> list[dict[str, Any]]:
    payload = _request("GET", "/v1/meetings", user_token, params={"limit": limit})
    return payload["items"]


def get_meeting(meeting_id: str, user_token: str) -> dict[str, Any]:
    return _request("GET", f"/v1/meetings/{meeting_id}", user_token)
