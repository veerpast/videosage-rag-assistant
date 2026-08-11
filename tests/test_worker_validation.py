import unittest

from worker.validation import validate_google_meet_url


class GoogleMeetUrlTests(unittest.TestCase):
    def test_accepts_standard_meeting_link(self):
        url = "https://meet.google.com/abc-defg-hij"
        self.assertEqual(validate_google_meet_url(url), url)

    def test_accepts_google_query_parameters(self):
        url = "https://meet.google.com/abc-defg-hij?authuser=0"
        self.assertEqual(validate_google_meet_url(url), url)

    def test_rejects_non_google_host(self):
        with self.assertRaises(ValueError):
            validate_google_meet_url("https://example.com/abc-defg-hij")

    def test_rejects_invalid_meeting_code(self):
        with self.assertRaises(ValueError):
            validate_google_meet_url("https://meet.google.com/not-a-code")


if __name__ == "__main__":
    unittest.main()
