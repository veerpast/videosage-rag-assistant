import os
import re
import yt_dlp
from pydub import AudioSegment
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter

DOWNLOAD_DIR = 'downloads'
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

def extract_youtube_id(url: str) -> str:
    """Extracts 11-character video ID from a YouTube URL."""
    match = re.search(r"(?:v=|\/|vi=|_|ch=)([0-9A-Za-z_-]{11})", url)
    return match.group(1) if match else ""

def fetch_fast_transcript(url: str) -> str:
    """Attempts to fetch captions directly without downloading audio."""
    video_id = extract_youtube_id(url)
    if not video_id:
        return None
    try:
        # FIX: Instantiate the API class first, then use .fetch() instead of .get_transcript()
        yt_api = YouTubeTranscriptApi()
        transcript_list = yt_api.fetch(video_id, languages=['en', 'en-US', 'en-GB', 'hi'])
        
        formatter = TextFormatter()
        return formatter.format_transcript(transcript_list)
    except Exception as e:
        print(f"Fast transcript path skipped/failed: {e}")
        return None

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
        "extractor_args": {
            "youtube": ["player_client=android,web"]
        },
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info).replace(".webm", ".wav").replace(".m4a", ".wav")
    return filename

def convert_to_wav(input_path: str) -> str:
    """Convert any audio/video file to WAV format using pydub."""
    output_path = os.path.splitext(input_path)[0] + "_converted.wav"
    audio = AudioSegment.from_file(input_path)
    audio = audio.set_channels(1).set_frame_rate(16000) # 16khz
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

def process_input(source: str):
    if source.startswith("http://") or source.startswith("https://"):
        print("Detected YouTube URL. Trying Fast Path (transcript extraction)...")
        fast_transcript = fetch_fast_transcript(source)
        if fast_transcript:
            print("Fast Path successful! Transcript retrieved directly without downloading audio.")
            return fast_transcript
        
        print("Fast Path unavailable or failed. Falling back to downloading audio...")
        wav_path = download_youtube_audio(source)
    else:
        print("Detected local file. Converting to WAV...")
        wav_path = convert_to_wav(source)

    print("Chunking audio...")
    chunks = chunk_audio(wav_path)
    print(f"Audio ready — {len(chunks)} chunk(s) created.")
    return chunks