"""PulseAudio monitor recording through FFmpeg."""

from __future__ import annotations

import shutil
import signal
import subprocess
from pathlib import Path


class PulseAudioRecorder:
    def __init__(self, sink_name: str, output_path: Path):
        self.sink_name = sink_name
        self.output_path = output_path
        self.process: subprocess.Popen[str] | None = None

    def start(self) -> None:
        if not shutil.which("ffmpeg"):
            raise RuntimeError("FFmpeg is not installed on the worker.")
        self._assert_sink_exists()
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self.process = subprocess.Popen(
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "warning",
                "-y",
                "-f",
                "pulse",
                "-i",
                f"{self.sink_name}.monitor",
                "-ac",
                "1",
                "-ar",
                "16000",
                "-c:a",
                "pcm_s16le",
                str(self.output_path),
            ],
            text=True,
        )

    def stop(self) -> None:
        if not self.process or self.process.poll() is not None:
            return
        self.process.send_signal(signal.SIGINT)
        try:
            self.process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            self.process.terminate()
            self.process.wait(timeout=5)

        if self.process.returncode not in {0, 255}:
            raise RuntimeError(
                f"FFmpeg recording failed with code {self.process.returncode}."
            )
        if not self.output_path.exists() or self.output_path.stat().st_size < 44:
            raise RuntimeError("The meeting recording is empty.")

    def _assert_sink_exists(self) -> None:
        result = subprocess.run(
            ["pactl", "list", "short", "sinks"],
            check=True,
            capture_output=True,
            text=True,
        )
        sink_names = {
            line.split("\t")[1] for line in result.stdout.splitlines() if "\t" in line
        }
        if self.sink_name not in sink_names:
            raise RuntimeError(
                f"PulseAudio sink {self.sink_name!r} is unavailable. "
                "Run the Oracle worker bootstrap script first."
            )
