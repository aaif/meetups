import io
import os
import sys
import unittest
from contextlib import redirect_stdout

sys.path.insert(0, os.path.dirname(__file__))
import intake  # noqa: E402


def _digest_of(rec):
    data = {"Organizers": [rec], "Hosts": [], "Speakers": []}
    buf = io.StringIO()
    with redirect_stdout(buf):
        intake.text_digest(data)
    return buf.getvalue()


BASE = {"row": 2, "status": "New", "Full name": "Ada", "Email": "ada@x.com"}


class TestDigestCity(unittest.TestCase):
    def test_shows_city_new_when_present(self):
        out = _digest_of({**BASE, "City (Existing)": "Other", "City (New)": "Berlin"})
        self.assertIn("Berlin", out)
        self.assertNotIn("Other", out)

    def test_falls_back_to_city_existing_when_new_blank(self):
        out = _digest_of({**BASE, "City (Existing)": "Paris", "City (New)": ""})
        self.assertIn("Paris", out)

    def test_city_not_double_printed_in_detail_block(self):
        out = _digest_of({**BASE, "City (Existing)": "Paris", "City (New)": ""})
        self.assertEqual(out.count("Paris"), 1)


class TestLegacyAliases(unittest.TestCase):
    def test_new_headers_map_to_legacy(self):
        self.assertEqual(intake.LEGACY_ALIASES["City (Existing)"], "City")
        self.assertEqual(intake.LEGACY_ALIASES["City (New)"], "Resolved City")


if __name__ == "__main__":
    unittest.main()
