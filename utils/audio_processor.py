import logging
import os
import re
from collections.abc import Callable
from urllib.parse import parse_qs, urlparse

import requests
import yt_dlp
from pydub import AudioSegment
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter
from yt_dlp.networking.impersonate import ImpersonateTarget

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)
LOGGER = logging.getLogger(__name__)
EDGE_TRANSCRIPT_URL = os.getenv(
    "YOUTUBE_TRANSCRIPT_FALLBACK_URL",
    "https://youtube-transcript.ai/transcript/{video_id}.txt",
).strip()


def extract_youtube_id(url: str) -> str:
    """Extracts 11-character video ID from a YouTube URL."""
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if host == "youtu.be":
        candidate = parsed.path.lstrip("/").split("/", 1)[0]
    elif host in {"youtube.com", "www.youtube.com", "m.youtube.com"}:
        candidate = parse_qs(parsed.query).get("v", [""])[0]
        if not candidate and parsed.path.startswith("/shorts/"):
            candidate = parsed.path.split("/")[2]
    else:
        return ""
    return candidate if re.fullmatch(r"[0-9A-Za-z_-]{11}", candidate) else ""


def is_youtube_url(url: str) -> bool:
    return bool(extract_youtube_id(url))


def fetch_edge_transcript(video_id: str, language: str = "en") -> str | None:
    """Fetch public captions through a low-volume edge fallback.

    Cloud hosting IPs are frequently blocked by YouTube even for caption-only
    requests. This provider accepts only the validated public video ID; no user
    token, account cookie, uploaded media, or private data is sent.
    """
    if not EDGE_TRANSCRIPT_URL or not re.fullmatch(r"[0-9A-Za-z_-]{11}", video_id):
        return None

    endpoint = EDGE_TRANSCRIPT_URL.format(video_id=video_id)
    try:
        response = requests.get(
            endpoint,
            params={"lang": language},
            headers={"Accept": "text/markdown, text/plain;q=0.9"},
            timeout=15,
        )
        response.raise_for_status()
        if len(response.content) > 5_000_000:
            raise ValueError("Transcript response exceeded the 5 MB safety limit.")
        transcript = response.text.strip()
        if len(transcript) < 40:
            return None

        # Remove provider metadata and keep the timestamped transcript body.
        body_start = re.search(r"(?m)^\[\d{1,2}:\d{2}(?::\d{2})?\]", transcript)
        if "# Transcript:" not in transcript or not body_start:
            return None
        return transcript[body_start.start() :]
    except (requests.RequestException, ValueError) as exc:
        LOGGER.warning("Edge transcript fallback failed: %s", type(exc).__name__)
        return None


def fetch_fast_transcript(
    url: str,
    fallback: Callable[[str], str | None] | None = None,
) -> str | None:
    """Attempts to fetch captions directly without downloading audio."""
    video_id = extract_youtube_id(url)
    if not video_id:
        return None
    try:
        # FIX: Instantiate the API class first, then use .fetch() instead of .get_transcript()
        yt_api = YouTubeTranscriptApi()
        transcript_list = yt_api.fetch(
            video_id, languages=["en", "en-US", "en-GB", "hi"]
        )

        formatter = TextFormatter()
        return formatter.format_transcript(transcript_list)
    except Exception as exc:  # noqa: BLE001 - provider exceptions vary by release
        LOGGER.warning("Direct transcript path failed: %s", type(exc).__name__)

    # The edge path keeps captioned YouTube analysis usable when YouTube blocks
    # Streamlit/Oracle datacenter IPs. It is deliberately caption-only.
    return fallback(video_id) if fallback else fetch_edge_transcript(video_id)


def download_youtube_audio(url: str) -> str:
    output_path = os.path.join(DOWNLOAD_DIR, "%(title)s.%(ext)s")
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": output_path,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "wav",
                "preferredquality": "192",
            }
        ],
        "quiet": True,
        # Only the slow path impersonates a browser. This gives yt-dlp a
        # browser-like TLS fingerprint when YouTube blocks cloud requests.
        "impersonate": ImpersonateTarget(client="chrome"),
        "extractor_args": {"youtube": ["player_client=android,web"]},
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = (
            ydl.prepare_filename(info).replace(".webm", ".wav").replace(".m4a", ".wav")
        )
    return filename


def convert_to_wav(input_path: str) -> str:
    """Convert any audio/video file to WAV format using pydub."""
    output_path = os.path.splitext(input_path)[0] + "_converted.wav"
    audio = AudioSegment.from_file(input_path)
    audio = audio.set_channels(1).set_frame_rate(16000)  # 16khz
    audio.export(output_path, format="wav")
    return output_path


def chunk_audio(wav_path: str, chunk_minutes: int = 10) -> list:
    audio = AudioSegment.from_wav(wav_path)
    chunk_ms = chunk_minutes * 60 * 1000

    chunks = []

    for i, start in enumerate(range(0, len(audio), chunk_ms)):
        chunk = audio[start : start + chunk_ms]
        chunk_path = f"{wav_path}_chunk_{i}.wav"
        chunk.export(chunk_path, format="wav")
        chunks.append(chunk_path)

    return chunks


def process_input(
    source: str,
    transcript_fallback: Callable[[str], str | None] | None = None,
):
    if source.startswith(("http://", "https://")):
        if not is_youtube_url(source):
            raise ValueError("Only valid YouTube URLs are supported.")
        print("Detected YouTube URL. Trying Fast Path (transcript extraction)...")
        fast_transcript = fetch_fast_transcript(source, transcript_fallback)
        if fast_transcript:
            print(
                "Fast Path successful! Transcript retrieved directly without downloading audio."
            )
            return fast_transcript

        print("Fast Path unavailable or failed. Falling back to downloading audio...")
        try:
            wav_path = download_youtube_audio(source)
        except yt_dlp.utils.DownloadError as exc:
            raise RuntimeError(
                "YouTube captions are unavailable and YouTube blocked the cloud "
                "audio fallback. Upload the media file directly instead."
            ) from exc
    else:
        print("Detected local file. Converting to WAV...")
        wav_path = convert_to_wav(source)

    print("Chunking audio...")
    chunks = chunk_audio(wav_path)
    print(f"Audio ready — {len(chunks)} chunk(s) created.")
    return chunks
