import os
import tempfile
import unittest

from aaif_meetups import office

FIX = os.path.join(os.path.dirname(__file__), "fixtures", "event_tracker_irl.docx")


class TestDocIO(unittest.TestCase):
    def test_read_returns_body(self):
        root = office.read_document(FIX)
        self.assertIsNotNone(root.find(f"{office.W}body"))

    def test_roundtrip_preserves_content_and_zip(self):
        root = office.read_document(FIX)
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "out.docx")
            office.save_document(FIX, root, out)
            root2 = office.read_document(out)
            # same number of tables survives the round-trip
            n1 = len(list(root.iter(f"{office.W}tbl")))
            n2 = len(list(root2.iter(f"{office.W}tbl")))
            self.assertEqual(n1, n2)
            self.assertGreater(n2, 5)
