import unittest

from utils.audio_processor import extract_youtube_id, is_youtube_url


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


if __name__ == "__main__":
    unittest.main()
