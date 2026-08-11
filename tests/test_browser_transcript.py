import unittest

from services.browser_transcript import _validated_transcript


class BrowserTranscriptValidationTests(unittest.TestCase):
    def test_accepts_matching_timestamped_transcript(self):
        payload = {
            "videoId": "_Q-e_nczWqM",
            "transcript": "# Transcript: Demo\n\n[0:00] Hello\n[0:02] World",
        }

        result = _validated_transcript(payload, "_Q-e_nczWqM")

        self.assertEqual(result, "[0:00] Hello\n[0:02] World")

    def test_rejects_response_for_different_video(self):
        payload = {
            "videoId": "jNQXAC9IVRw",
            "transcript": "# Transcript: Demo\n\n[0:00] Hello there",
        }

        self.assertIsNone(_validated_transcript(payload, "_Q-e_nczWqM"))

    def test_rejects_provider_marketing_or_rate_limit_text(self):
        payload = {
            "videoId": "_Q-e_nczWqM",
            "transcript": "You have made too many requests. Please upgrade.",
        }

        self.assertIsNone(_validated_transcript(payload, "_Q-e_nczWqM"))


if __name__ == "__main__":
    unittest.main()
