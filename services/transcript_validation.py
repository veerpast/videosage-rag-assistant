"""Validation helpers for untrusted browser caption payloads."""

from __future__ import annotations

import re

VIDEO_ID_RE = re.compile(r"^[0-9A-Za-z_-]{11}$")
_TIMESTAMP_RE = re.compile(r"(?m)^\[\d{1,2}:\d{2}(?::\d{2})?\]")
_MAX_TRANSCRIPT_CHARS = 5_000_000


def validated_browser_transcript(payload: object, expected_video_id: str) -> str | None:
    """Validate an untrusted component payload and extract its transcript body."""
    if not isinstance(payload, dict) or payload.get("videoId") != expected_video_id:
        return None
    transcript = payload.get("transcript")
    if (
        not isinstance(transcript, str)
        or not 40 <= len(transcript) <= _MAX_TRANSCRIPT_CHARS
    ):
        return None
    if "# Transcript:" not in transcript:
        return None
    body_start = _TIMESTAMP_RE.search(transcript)
    return transcript[body_start.start() :].strip() if body_start else None
