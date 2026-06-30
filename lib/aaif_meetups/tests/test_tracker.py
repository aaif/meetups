import datetime as dt
import unittest

from aaif_meetups import tracker


class TestDates(unittest.TestCase):
    def test_parse_event_date(self):
        self.assertEqual(
            tracker.parse_event_date("Tue · June 24, 2026 · 17:30 — late"),
            dt.date(2026, 6, 24))

    def test_parse_due_infers_year(self):
        anchor = dt.date(2026, 6, 24)
        self.assertEqual(tracker.parse_due("May 27", anchor), dt.date(2026, 5, 27))
        self.assertEqual(tracker.parse_due("Jun 3", anchor), dt.date(2026, 6, 3))

    def test_parse_due_skips_clock_and_blank(self):
        anchor = dt.date(2026, 6, 24)
        self.assertIsNone(tracker.parse_due("16:00", anchor))
        self.assertIsNone(tracker.parse_due("", anchor))

    def test_restamp_shifts_dates_keeps_clock(self):
        old, new = dt.date(2026, 6, 24), dt.date(2026, 7, 8)  # +14 days
        self.assertEqual(tracker.restamp("May 27", old, new), "Jun 10")
        self.assertEqual(tracker.restamp("16:00", old, new), "16:00")
        self.assertEqual(tracker.restamp("", old, new), "")
