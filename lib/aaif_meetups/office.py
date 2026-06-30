"""Stdlib-only OOXML helpers: read/write word/document.xml inside a .docx zip,
and navigate/edit its tables, rows, cells, and paragraph run text."""
import zipfile
from xml.etree import ElementTree as ET

NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W = "{%s}" % NS
ET.register_namespace("w", NS)


def read_document(path):
    with zipfile.ZipFile(path) as z:
        return ET.fromstring(z.read("word/document.xml"))


def save_document(src_path, root, out_path):
    body = ET.tostring(root, encoding="UTF-8", xml_declaration=True)
    with zipfile.ZipFile(src_path) as zin:
        names = zin.namelist()
        data = {n: zin.read(n) for n in names}
    data["word/document.xml"] = body
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zo:
        for n in names:
            zo.writestr(n, data[n])


def tables(root):
    return list(root.iter(W + "tbl"))


def rows(tbl):
    return tbl.findall(W + "tr")


def cells(tr):
    return tr.findall(W + "tc")


def _texts(el):
    return list(el.iter(W + "t"))


def cell_text(tc):
    return "".join(t.text or "" for t in _texts(tc)).strip()


def para_text(p):
    return "".join(t.text or "" for t in _texts(p)).strip()


def set_cell_text(tc, text):
    ts = _texts(tc)
    if not ts:
        raise ValueError("cell has no run text node to set")
    ts[0].text = text
    # xml:space=preserve guards against trimming
    ts[0].set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    for extra in ts[1:]:
        extra.text = ""
