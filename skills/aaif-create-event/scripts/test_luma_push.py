#!/usr/bin/env python3
import pathlib
import sys
import unittest
from unittest import mock

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

    def test_levels_match_case_insensitively(self):
        # "Check-In" must not silently become a display name with manager access
        self.assertEqual(luma_push.parse_host("a@b.co:Check-In"), ("a@b.co", "check-in", None))
        self.assertEqual(luma_push.parse_host("a@b.co:MANAGER:Maya Chen"),
                         ("a@b.co", "manager", "Maya Chen"))

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

    def test_connected_aaif_event_slug_counts_as_pushed(self):
        # event pages may use aaif- slugs too — the entity lookup, not the slug,
        # decides, so an aaif- event page must NOT bypass the duplicate-create abort
        with mock.patch.object(luma_push.luma, "resolve_event_id", return_value="evt-1"):
            self.assertEqual(
                luma_push.already_pushed(view("https://luma.com/aaif-sf-evalnight"),
                                         connected=True),
                "https://luma.com/aaif-sf-evalnight")

    def test_connected_calendar_link_does_not(self):
        with mock.patch.object(luma_push.luma, "resolve_event_id",
                               side_effect=luma_push.luma.NotAnEventUrl("calendar")):
            self.assertIsNone(luma_push.already_pushed(view("luma.com/aaif-sanfrancisco"),
                                                       connected=True))

    def test_connected_lookup_failure_raises_not_guesses(self):
        # fail closed: an inconclusive lookup must surface, never silently fall
        # back to the slug heuristic right before a live --create
        with mock.patch.object(luma_push.luma, "resolve_event_id",
                               side_effect=luma_push.luma.LumaError("HTTP 500")):
            with self.assertRaises(luma_push.luma.LumaError):
                luma_push.already_pushed(view("https://luma.com/aaif-sf-evalnight"),
                                         connected=True)


if __name__ == "__main__":
    unittest.main()
