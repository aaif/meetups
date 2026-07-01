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


class TestTablePrimitives(unittest.TestCase):
    def setUp(self):
        self.root = office.read_document(FIX)

    def test_detail_table_first_row(self):
        # the detail table's first row is ["EVENT TITLE", <value>]
        detail = [t for t in office.tables(self.root)
                  if office.cell_text(office.cells(office.rows(t)[0])[0]) == "EVENT TITLE"]
        self.assertEqual(len(detail), 1)
        first = office.rows(detail[0])[0]
        self.assertEqual(office.cell_text(office.cells(first)[0]), "EVENT TITLE")

    def test_set_cell_text_roundtrips(self):
        detail = next(t for t in office.tables(self.root)
                      if office.cell_text(office.cells(office.rows(t)[0])[0]) == "EVENT TITLE")
        value_cell = office.cells(office.rows(detail)[0])[1]
        office.set_cell_text(value_cell, "New Night · Test Series")
        self.assertEqual(office.cell_text(value_cell), "New Night · Test Series")


class TestSaveFidelity(unittest.TestCase):
    def test_save_preserves_namespace_prefixes(self):
        import re
        import zipfile
        root = office.read_document(FIX)
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "o.docx")
            office.save_document(FIX, root, out)
            xml = zipfile.ZipFile(out).read("word/document.xml").decode("utf8", "ignore")
        # no auto-generated ns0:/ns1:/ns2: prefixes; r:id relationship refs intact
        self.assertEqual(re.findall(r"\bns\d+:", xml), [])
        self.assertIn("r:id=", xml)


class TestSetCellTextEmpty(unittest.TestCase):
    def test_raises_when_cell_has_no_run(self):
        from xml.etree import ElementTree as ET
        tc = ET.fromstring('<w:tc xmlns:w="%s"><w:p/></w:tc>' % office.NS)
        with self.assertRaises(ValueError):
            office.set_cell_text(tc, "x")
