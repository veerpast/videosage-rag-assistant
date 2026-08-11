import unittest
from unittest.mock import patch

from utils.audio_processor import (
    extract_youtube_id,
    fetch_fast_transcript,
    is_youtube_url,
)


class YouTubeUrlTests(unittest.TestCase):
    def test_extracts_watch_url(self):
        self.assertEqual(
            extract_youtube_id("https://www.youtube.com/watch?v=_Q-e_nczWqM&t=1"),
            "_Q-e_nczWqM",
        )

    def test_extracts_short_url(self):
        self.assertEqual(
            extract_youtube_id("https://youtu.be/_Q-e_nczWqM"),
            "_Q-e_nczWqM",
        )

    def test_rejects_non_youtube_url(self):
        self.assertFalse(is_youtube_url("https://example.com/watch?v=_Q-e_nczWqM"))

    @patch("utils.audio_processor.YouTubeTranscriptApi")
    def test_fast_path_uses_browser_transcript_after_cloud_block(self, transcript_api):
        transcript_api.return_value.fetch.side_effect = RuntimeError("blocked")

        transcript = fetch_fast_transcript(
            "https://youtu.be/_Q-e_nczWqM",
            browser_transcript="[0:00] Browser transcript",
        )

        self.assertEqual(transcript, "[0:00] Browser transcript")


if __name__ == "__main__":
    unittest.main()
