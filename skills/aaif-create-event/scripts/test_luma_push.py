#!/usr/bin/env python3
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import luma_push  # noqa: E402


def view(url):
    return {"details": {"LUMA URL": url}}


class TestParseHost(unittest.TestCase):
    def test_forms(self):
        self.assertEqual(luma_push.parse_host("a@b.co"), ("a@b.co", None, None))
        self.assertEqual(luma_push.parse_host("a@b.co:check-in"), ("a@b.co", "check-in", None))
        self.assertEqual(luma_push.parse_host("a@b.co:manager:Maya Chen"),
                         ("a@b.co", "manager", "Maya Chen"))
        self.assertEqual(luma_push.parse_host("a@b.co:Maya Chen"),
                         ("a@b.co", None, "Maya Chen"))

    def test_rejects_non_email(self):
        with self.assertRaises(ValueError):
            luma_push.parse_host("not-an-email")


class TestAlreadyPushed(unittest.TestCase):
    def test_event_page_url_counts_as_pushed(self):
        self.assertEqual(luma_push.already_pushed(view("https://luma.com/ia70fwmm")),
                         "https://luma.com/ia70fwmm")
        self.assertTrue(luma_push.already_pushed(view("lu.ma/xyz123")))

    def test_calendar_link_or_empty_does_not(self):
        # the template pre-fills the CHAPTER calendar link; that's not a pushed event
        self.assertIsNone(luma_push.already_pushed(view("luma.com/aaif-sanfrancisco")))
        self.assertIsNone(luma_push.already_pushed(view("")))
        self.assertIsNone(luma_push.already_pushed(view("TBD")))


if __name__ == "__main__":
    unittest.main()
