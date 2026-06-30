import datetime as dt
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__),
                                                 "..", "..", "..", "lib")))
sys.path.insert(0, os.path.dirname(__file__))
import event_status  # noqa: E402


class TestClassify(unittest.TestCase):
    def test_overdue_and_due_soon(self):
        today = dt.date(2026, 6, 10)
        tasks = [
            {"task": "A", "owner": "Org", "due": "Jun 3", "status": "Not started"},   # overdue
            {"task": "B", "owner": "Org", "due": "Jun 12", "status": "Not started"},  # due soon
            {"task": "C", "owner": "Org", "due": "Jun 3", "status": "Done"},          # done -> ignore
            {"task": "D", "owner": "Co", "due": "16:00", "status": "Not started"},    # clock -> ignore
        ]
        anchor = dt.date(2026, 6, 24)
        res = event_status.classify(tasks, anchor, today)
        self.assertEqual([t["task"] for t in res["overdue"]], ["A"])
        self.assertEqual([t["task"] for t in res["due_soon"]], ["B"])


if __name__ == "__main__":
    unittest.main()
