"""Small validation helpers shared by the worker API and tests."""

from __future__ import annotations

import re
from urllib.parse import urlparse

MEET_PATH = re.compile(r"/[a-z]{3}-[a-z]{4}-[a-z]{3}/?")


def validate_google_meet_url(value: str) -> str:
    cleaned = value.strip()
    parsed = urlparse(cleaned)
    if parsed.scheme != "https" or parsed.hostname != "meet.google.com":
        raise ValueError("meeting_url must be an https://meet.google.com URL")
    if not MEET_PATH.fullmatch(parsed.path):
        raise ValueError("meeting_url must contain a valid Google Meet code")
    return cleaned
