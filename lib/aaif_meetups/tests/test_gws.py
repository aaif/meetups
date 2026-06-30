import unittest

from aaif_meetups import gws


class TestGwsModule(unittest.TestCase):
    def test_exposes_callables_and_mime(self):
        for name in ("gws_json", "gws_download", "gws_upload",
                     "list_children", "find_child"):
            self.assertTrue(callable(getattr(gws, name)), name)
        self.assertIn("wordprocessingml", gws.DOCX)
