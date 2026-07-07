import datetime as dt
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__),
                                                 "..", "..", "..", "lib")))
sys.path.insert(0, os.path.dirname(__file__))
import event_status  # noqa: E402
from aaif_events.tracker import Task  # noqa: E402


class TestClassify(unittest.TestCase):
    def test_overdue_and_due_soon(self):
        today = dt.date(2026, 6, 10)
        tasks = [
            Task("A", "Org", "Jun 3", "Not started"),    # overdue
            Task("B", "Org", "Jun 12", "Not started"),   # due soon
            Task("C", "Org", "Jun 3", "Done"),           # done -> ignore
            Task("D", "Co", "16:00", "Not started"),     # clock -> ignore
        ]
        anchor = dt.date(2026, 6, 24)
        res = event_status.classify(tasks, anchor, today)
        self.assertEqual([t.task for t in res["overdue"]], ["A"])
        self.assertEqual([t.task for t in res["due_soon"]], ["B"])


if __name__ == "__main__":
    unittest.main()
