"""Browser-side public YouTube caption retrieval for Streamlit Cloud.

YouTube commonly blocks datacenter IPs used by Streamlit and Oracle. The tiny
component below performs the caption-only request from the signed-in user's
browser instead. Only a validated public video ID and language code leave the
browser; account tokens, cookies, and uploaded media are never included.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

import streamlit as st

_VIDEO_ID_RE = re.compile(r"^[0-9A-Za-z_-]{11}$")
_TIMESTAMP_RE = re.compile(r"(?m)^\[\d{1,2}:\d{2}(?::\d{2})?\]")
_MAX_TRANSCRIPT_CHARS = 5_000_000

_CAPTION_COMPONENT = st.components.v2.component(
    name="videosage_browser_captions",
    html='<span class="caption-probe" aria-hidden="true"></span>',
    css=".caption-probe { display: none; }",
    js=r"""
const requests = new Map();

export default function({ data, setStateValue }) {
  const videoId = data?.videoId;
  const language = data?.language || "en";
  const requestId = data?.requestId;
  const resolvedRequestId = data?.resolvedRequestId;
  if (!videoId || !requestId || requestId === resolvedRequestId || requests.has(requestId)) return;

  const request = fetch(
    `https://youtube-transcript.ai/transcript/${encodeURIComponent(videoId)}.txt?lang=${encodeURIComponent(language)}`,
    { headers: { Accept: "text/markdown, text/plain;q=0.9" } },
  )
    .then(async (response) => {
      if (!response.ok) throw new Error(`Caption service returned ${response.status}`);
      const text = await response.text();
      setStateValue("result", { requestId, videoId, transcript: text, error: null });
    })
    .catch(() => {
      setStateValue("result", {
        requestId, videoId,
        transcript: null,
        error: "Public captions could not be retrieved.",
      });
    })
    .finally(() => requests.delete(requestId));

  requests.set(requestId, request);
}
""",
)


@dataclass(frozen=True)
class BrowserTranscript:
    status: Literal["idle", "loading", "ready", "unavailable"]
    video_id: str = ""
    transcript: str | None = None


def _validated_transcript(payload: object, expected_video_id: str) -> str | None:
    """Validate the untrusted component payload and extract its transcript body."""
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


def get_browser_transcript(video_id: str, language: str = "en") -> BrowserTranscript:
    """Render the hidden caption fetcher and return its validated state."""
    if not _VIDEO_ID_RE.fullmatch(video_id):
        return BrowserTranscript(status="idle")

    attempt_key = f"browser_caption_attempt:{video_id}:{language}"
    attempt = int(st.session_state.get(attempt_key, 0))
    request_id = f"{video_id}:{language}:{attempt}"
    cache_key = f"browser_caption:{request_id}"
    cached = st.session_state.get(cache_key)
    resolved_request_id = cached.get("requestId") if isinstance(cached, dict) else None
    component_result = _CAPTION_COMPONENT(
        key=f"caption-fetch-{request_id}",
        data={
            "videoId": video_id,
            "language": language,
            "requestId": request_id,
            "resolvedRequestId": resolved_request_id,
        },
        default={"result": cached},
        on_result_change=lambda: None,
        height=0,
    )
    payload = component_result.result
    if isinstance(payload, dict) and payload.get("videoId") == video_id:
        st.session_state[cache_key] = payload
    else:
        payload = cached

    if not isinstance(payload, dict) or payload.get("videoId") != video_id:
        return BrowserTranscript(status="loading", video_id=video_id)
    transcript = _validated_transcript(payload, video_id)
    if transcript:
        return BrowserTranscript(
            status="ready", video_id=video_id, transcript=transcript
        )
    return BrowserTranscript(status="unavailable", video_id=video_id)


def retry_browser_transcript(video_id: str, language: str = "en") -> None:
    """Start a fresh browser request after a transient caption failure."""
    if not _VIDEO_ID_RE.fullmatch(video_id):
        return
    attempt_key = f"browser_caption_attempt:{video_id}:{language}"
    st.session_state[attempt_key] = int(st.session_state.get(attempt_key, 0)) + 1
