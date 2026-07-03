"""Unit tests for the network-map marker placement in create_chapter.py.

Run: python3 skills/aaif-create-chapter/scripts/test_create_chapter.py
"""
import os
import re
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, os.path.dirname(__file__))
import create_chapter as cc  # noqa: E402

A = 'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"'
P = 'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"'

# Slide-5 shape templates, mirroring the real deck. The DOT is the square
# 155448x155448 shape and carries an EMPTY <a:t></a:t> (so text presence can NOT
# distinguish it from the label). The LABEL is a wide text box whose <a:t> carries
# xml:space="preserve" the way rebrand_file leaves it. Discrimination is by ext.
DOT_SP = (
    '<p:sp><p:spPr><a:xfrm><a:off x="4074942" y="2650779"/>'
    '<a:ext cx="155448" cy="155448"/></a:xfrm>'
    '<a:solidFill><a:srgbClr val="14964A"/></a:solidFill></p:spPr>'
    '<p:txBody><a:p><a:r><a:t></a:t></a:r></a:p></p:txBody></p:sp>'
)
LABEL_SP = (
    '<p:sp><p:spPr><a:xfrm><a:off x="3649553" y="2875998"/>'
    '<a:ext cx="2000000" cy="300000"/></a:xfrm>'
    '<a:solidFill><a:srgbClr val="14964A"/></a:solidFill></p:spPr>'
    '<p:txBody><a:p><a:r>'
    '<a:t xml:space="preserve">SAN FRANCISCO · TONIGHT</a:t>'
    '</a:r></a:p></p:txBody></p:sp>'
)
# A non-green decorative shape that must never move.
OTHER_SP = (
    '<p:sp><p:spPr><a:xfrm><a:off x="111111" y="222222"/>'
    '<a:ext cx="500000" cy="500000"/></a:xfrm>'
    '<a:solidFill><a:srgbClr val="FFFFFF"/></a:solidFill></p:spPr></p:sp>'
)


def slide5(*shapes):
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<p:sld %s %s><p:cSld><p:spTree>%s</p:spTree></p:cSld></p:sld>'
            % (P, A, "".join(shapes)))


def make_pptx(path, slide_xml=None):
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", "<Types/>")
        if slide_xml is not None:
            z.writestr(cc.SLIDE5, slide_xml)


def offsets_by_shape(path):
    """Return {'dot': (x, y), 'label': (x, y), 'other': (x, y)} from slide 5."""
    with zipfile.ZipFile(path) as z:
        xml = z.read(cc.SLIDE5).decode("utf-8")
    out = {}
    for block in re.findall(r"<p:sp\b[^>]*>.*?</p:sp>", xml, re.S):
        m = re.search(r'<a:off x="(-?\d+)" y="(-?\d+)"/>', block)
        xy = (int(m.group(1)), int(m.group(2)))
        if "14964A" not in block:
            out["other"] = xy
        elif cc.DOT_EXT_RE.search(block):
            out["dot"] = xy
        else:
            out["label"] = xy
    return out


class TestProjection(unittest.TestCase):
    def test_sf_selfcheck_matches_real_deck(self):
        # Ground truth: the real San Francisco chapter deck's dot sits at exactly
        # this offset. The projection must reproduce it (this is the calibration
        # reference — do NOT replace it with a guessed value).
        dot_off, _ = cc.marker_offsets("San Francisco", 37.77, -122.42)
        self.assertEqual(dot_off, (4074942, 2650779))

    def test_label_keeps_template_offset_from_dot(self):
        dot_off, label_off = cc.marker_offsets("New York", 40.71, -74.01)
        self.assertEqual(label_off[0] - dot_off[0], cc.LABEL_DX)
        self.assertEqual(label_off[1] - dot_off[1], cc.LABEL_DY)

    def test_pixel_override_wins_over_formula(self):
        # Overridden cities ignore lat/lon entirely.
        self.assertEqual(cc.project_city("Seoul", 0.0, 0.0), (822, 305))
        self.assertEqual(cc.project_city("Sydney", 99.0, 99.0), (870, 512))


class TestReposition(unittest.TestCase):
    def test_moves_both_shapes_to_new_city(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "Slides.pptx")
            make_pptx(p, slide5(DOT_SP, LABEL_SP, OTHER_SP))
            moved = cc.reposition_map_marker(p, "New York", 40.71, -74.01)
            self.assertEqual(moved, 2)
            self.assertIsNone(zipfile.ZipFile(p).testzip())

            dot_off, label_off = cc.marker_offsets("New York", 40.71, -74.01)
            got = offsets_by_shape(p)
            self.assertEqual(got["dot"], dot_off)
            self.assertEqual(got["label"], label_off)      # label detected despite xml:space
            self.assertEqual(got["other"], (111111, 222222))  # untouched

    def test_uses_pixel_override_when_present(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "Slides.pptx")
            make_pptx(p, slide5(DOT_SP, LABEL_SP))
            # Seoul's lat/lon are deliberately wrong; the override must win.
            cc.reposition_map_marker(p, "Seoul", 0.0, 0.0)
            expected_dot, _ = cc.marker_offsets("Seoul", 0.0, 0.0)
            self.assertEqual(offsets_by_shape(p)["dot"], expected_dot)

    def test_absent_slide5_returns_zero(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "Slides.pptx")
            make_pptx(p, slide_xml=None)  # no slide 5 at all
            self.assertEqual(cc.reposition_map_marker(p, "New York", 40.71, -74.01), 0)

    def test_no_green_shapes_returns_zero(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "Slides.pptx")
            make_pptx(p, slide5(OTHER_SP))  # shapes present, none green
            self.assertEqual(cc.reposition_map_marker(p, "New York", 40.71, -74.01), 0)

    def test_guard_raises_when_not_exactly_two_green(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "Slides.pptx")
            make_pptx(p, slide5(DOT_SP, OTHER_SP))  # only 1 green shape
            with self.assertRaises(RuntimeError):
                cc.reposition_map_marker(p, "New York", 40.71, -74.01)


class TestResolveLatlon(unittest.TestCase):
    def test_override_bypasses_geocoding(self):
        # Both values given -> returned verbatim, no network.
        self.assertEqual(cc.resolve_latlon("Anywhere", 12.34, 56.78), (12.34, 56.78))

    def test_lone_value_falls_through_to_geocode(self):
        calls = []
        orig = cc.geocode_city
        cc.geocode_city = lambda name, **kw: calls.append(name) or (1.0, 2.0)
        try:
            self.assertEqual(cc.resolve_latlon("Paris", 48.85, None), (1.0, 2.0))
            self.assertEqual(calls, ["Paris"])
        finally:
            cc.geocode_city = orig

    def test_ungeocodable_returns_none(self):
        orig = cc.geocode_city
        cc.geocode_city = lambda name, **kw: None
        try:
            self.assertIsNone(cc.resolve_latlon("Tatooine", None, None))
        finally:
            cc.geocode_city = orig


if __name__ == "__main__":
    unittest.main()
