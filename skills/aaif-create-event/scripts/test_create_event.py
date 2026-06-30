import datetime as dt
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__),
                                                 "..", "..", "..", "lib")))
sys.path.insert(0, os.path.dirname(__file__))
import create_event  # noqa: E402
from aaif_meetups import office, tracker  # noqa: E402

FIX = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..",
                                   "lib", "aaif_meetups", "tests", "fixtures",
                                   "event_tracker_irl.docx"))


class TestCreateCore(unittest.TestCase):
    def test_apply_adds_event_to_local_docx(self):
        with tempfile.TemporaryDirectory() as d:
            local = os.path.join(d, "t.docx")
            shutil.copy(FIX, local)
            create_event.apply_local(local, {
                "EVENT TITLE": "Eval Night",
                "DATE & TIME": "Wed · August 12, 2026 · 18:00 — late",
            }, dt.date(2026, 8, 12))
            root = office.read_document(local)
            titles = [e["title"] for e in tracker.list_events(root)]
            self.assertIn("Eval Night", titles)


if __name__ == "__main__":
    unittest.main()
