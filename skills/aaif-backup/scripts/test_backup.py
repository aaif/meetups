import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(__file__))
import backup  # noqa: E402


class TestSlugify(unittest.TestCase):
    def test_normalizes_name(self):
        self.assertEqual(backup.slugify("AAIF Community Intake Ops"),
                         "aaif-community-intake-ops")

    def test_collapses_runs_and_strips_edges(self):
        self.assertEqual(backup.slugify("  --Foo!!Bar--  "), "foo-bar")

    def test_empty_or_garbage_falls_back(self):
        self.assertEqual(backup.slugify("   "), "backup")
        self.assertEqual(backup.slugify("!!!"), "backup")


class TestTimestamp(unittest.TestCase):
    def test_utc_filename_safe_format(self):
        self.assertRegex(backup.timestamp(), r"^\d{4}-\d{2}-\d{2}T\d{6}Z$")


class TestSnapshotPath(unittest.TestCase):
    def test_never_overwrites_within_same_second(self):
        with tempfile.TemporaryDirectory() as d:
            p1 = backup.snapshot_path(d, "s", "xlsx")
            open(p1, "w").close()
            p2 = backup.snapshot_path(d, "s", "xlsx")
            self.assertNotEqual(p1, p2)
            self.assertFalse(os.path.exists(p2))


class TestBackupLocal(unittest.TestCase):
    def test_copies_and_keeps_extension(self):
        with tempfile.TemporaryDirectory() as d:
            src = os.path.join(d, "thing.xlsx")
            with open(src, "w") as f:
                f.write("data")
            out = backup.backup_local(src, os.path.join(d, "bk"))
            self.assertTrue(out.endswith(".xlsx"))
            self.assertTrue(os.path.isfile(out))

    def test_no_extension_becomes_bin(self):
        with tempfile.TemporaryDirectory() as d:
            src = os.path.join(d, "noext")
            with open(src, "w") as f:
                f.write("x")
            out = backup.backup_local(src, os.path.join(d, "bk"))
            self.assertTrue(out.endswith(".bin"))

    def test_missing_file_exits_not_silent(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(SystemExit):
                backup.backup_local(os.path.join(d, "nope.xlsx"), d)


class TestDriveIdDispatch(unittest.TestCase):
    def test_id_shape_matches_but_paths_do_not(self):
        self.assertTrue(backup.DRIVE_ID_RE.match(backup.INTAKE_OPS_ID))
        self.assertIsNone(backup.DRIVE_ID_RE.match("./intake.xlsx"))
        self.assertIsNone(backup.DRIVE_ID_RE.match("intake.xlsx"))


if __name__ == "__main__":
    unittest.main()
