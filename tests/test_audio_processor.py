import unittest
from unittest.mock import MagicMock, patch

from utils.audio_processor import (
    extract_youtube_id,
    fetch_edge_transcript,
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

    @patch("utils.audio_processor.requests.get")
    def test_edge_transcript_strips_provider_metadata(self, mock_get):
        response = MagicMock()
        response.content = b"transcript"
        response.text = "# Transcript: Demo\n\n[0:00] Hello\n[0:02] World"
        mock_get.return_value = response

        transcript = fetch_edge_transcript("_Q-e_nczWqM")

        self.assertEqual(transcript, "[0:00] Hello\n[0:02] World")
        request_url = mock_get.call_args.args[0]
        self.assertNotIn("youtube.com", request_url)
        self.assertEqual(mock_get.call_args.kwargs["timeout"], 15)

    @patch("utils.audio_processor.requests.get")
    def test_edge_transcript_rejects_oversized_response(self, mock_get):
        response = MagicMock()
        response.content = b"x" * 5_000_001
        response.text = "[0:00] should not be accepted"
        mock_get.return_value = response

        self.assertIsNone(fetch_edge_transcript("_Q-e_nczWqM"))

    @patch("utils.audio_processor.YouTubeTranscriptApi")
    def test_fast_path_uses_injected_fallback_after_cloud_block(self, transcript_api):
        transcript_api.return_value.fetch.side_effect = RuntimeError("blocked")
        fallback = MagicMock(return_value="[0:00] Cloud-safe transcript")

        transcript = fetch_fast_transcript(
            "https://youtu.be/_Q-e_nczWqM", fallback=fallback
        )

        self.assertEqual(transcript, "[0:00] Cloud-safe transcript")
        fallback.assert_called_once_with("_Q-e_nczWqM")


if __name__ == "__main__":
    unittest.main()
