import datetime as dt
import os
import unittest

from aaif_meetups import gws_cli, office, tracker

FIX = os.path.join(os.path.dirname(__file__), "fixtures", "event_tracker_irl.docx")


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


class TestEventModel(unittest.TestCase):
    def setUp(self):
        self.root = office.read_document(FIX)

    def test_list_events_finds_the_example(self):
        evs = tracker.list_events(self.root)
        self.assertEqual(len(evs), 1)
        self.assertIn("Agentic AI Night", evs[0]["title"])
        # 4wk,3wk,2wk,1wk,day-before,day-of,next-day,follow-ups
        self.assertEqual(len(evs[0]["phase_tables"]), 8)

    def test_read_event_details_and_tasks(self):
        ev = tracker.read_event(self.root, "Agentic AI Night")
        self.assertEqual(ev["details"]["DATE & TIME"], "Tue · June 24, 2026 · 17:30 — late")
        self.assertEqual(ev["date"], dt.date(2026, 6, 24))
        self.assertEqual(ev["phases"][0]["tasks"][0]["status"], "Done")

    def test_read_event_next(self):
        ev = tracker.read_event(self.root, "next")
        self.assertIn("Agentic AI Night", ev["title"])


class TestWrites(unittest.TestCase):
    def setUp(self):
        self.root = office.read_document(FIX)

    def test_set_field(self):
        tracker.set_field(self.root, "Agentic AI Night", "SPEAKER(S)", "Jane Doe (Infra)")
        ev = tracker.read_event(self.root, "Agentic AI Night")
        self.assertEqual(ev["details"]["SPEAKER(S)"], "Jane Doe (Infra)")

    def test_set_due_dates_shifts_two_weeks(self):
        # original 4-weeks-out task due "May 27"; +14 days -> "Jun 10"
        changed = tracker.set_due_dates(self.root, "Agentic AI Night", dt.date(2026, 7, 8))
        self.assertGreater(changed, 0)
        ev = tracker.read_event(self.root, "Agentic AI Night")
        self.assertEqual(ev["phases"][0]["tasks"][0]["due"], "Jun 10")
        # day-of clock times unchanged
        dayof = ev["phases"][5]["tasks"][0]["due"]
        self.assertRegex(dayof, r"^\d{1,2}:\d{2}$")


class TestAddEvent(unittest.TestCase):
    def setUp(self):
        self.root = office.read_document(FIX)

    def test_add_event_appends_section(self):
        before = len(tracker.list_events(self.root))
        tracker.add_event(self.root, {
            "EVENT TITLE": "Eval Night · Builder Series",
            "DATE & TIME": "Wed · August 12, 2026 · 18:00 — late",
            "SPEAKER(S)": "TBD",
        }, dt.date(2026, 8, 12))
        evs = tracker.list_events(self.root)
        self.assertEqual(len(evs), before + 1)
        new = tracker.read_event(self.root, "Eval Night")
        self.assertEqual(new["details"]["EVENT TITLE"], "Eval Night · Builder Series")
        # statuses reset
        self.assertTrue(all(t["status"] == "Not started"
                            for ph in new["phases"] for t in ph["tasks"]))
        # dates restamped to the new event date (4-wks-out is ~28 days before Aug 12)
        self.assertNotEqual(new["phases"][0]["tasks"][0]["due"], "May 27")
        # the appended section survives a save -> reload (no corruption)
        import tempfile
        with tempfile.TemporaryDirectory() as dd:
            out = os.path.join(dd, "out.docx")
            office.save_document(FIX, self.root, out)
            reloaded = office.read_document(out)
            self.assertEqual(len(tracker.list_events(reloaded)), before + 1)


class TestLocate(unittest.TestCase):
    def test_locate_prefers_chapters_then_online(self):
        def fake_children(folder_id):
            if folder_id == tracker.CHAPTERS_PARENT:
                return [{"id": "fA", "name": "Berlin",
                         "mimeType": "application/vnd.google-apps.folder"}]
            if folder_id == "fA":
                return [{"id": "tDoc", "name": "Event Tracker.docx"}]
            return []
        orig = gws_cli.list_children
        gws_cli.list_children = fake_children
        try:
            got = tracker.locate_tracker("berlin")
        finally:
            gws_cli.list_children = orig
        self.assertEqual(got["file_id"], "tDoc")
        self.assertEqual(got["kind"], "chapter")
