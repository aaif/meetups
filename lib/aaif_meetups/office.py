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
