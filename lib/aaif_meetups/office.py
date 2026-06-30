"""Stdlib-only OOXML helpers: read/write word/document.xml inside a .docx zip,
and navigate/edit its tables, rows, cells, and paragraph run text."""
import re
import zipfile
from xml.etree import ElementTree as ET

NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W = "{%s}" % NS
ET.register_namespace("w", NS)

_XMLNS_RE = re.compile(rb'xmlns:([A-Za-z0-9_]+)="([^"]+)"')


def _register_namespaces(xml_bytes):
    """Register every xmlns prefix declared in the document so ElementTree
    serializes with the original prefixes (e.g. `r:id`, `mc:Ignorable`) instead of
    auto-generated `ns0:`/`ns1:` ones. Without this, re-serializing renames every
    namespaced attribute and can make Word reject the file."""
    for m in _XMLNS_RE.finditer(xml_bytes):
        prefix, uri = m.group(1).decode(), m.group(2).decode()
        try:
            ET.register_namespace(prefix, uri)
        except ValueError:
            pass  # reserved prefixes like "xml"


def read_document(path):
    with zipfile.ZipFile(path) as z:
        data = z.read("word/document.xml")
    _register_namespaces(data)
    return ET.fromstring(data)


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


def _set_runs_text(el, text):
    """Write `text` into the first run's <w:t> of `el`, blank every other <w:t>
    (preserves the element's run formatting). Returns False if there is no run."""
    ts = _texts(el)
    if not ts:
        return False
    ts[0].text = text
    # xml:space=preserve guards against trimming
    ts[0].set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    for extra in ts[1:]:
        extra.text = ""
    return True


def set_cell_text(tc, text):
    # NOTE: updates the cell's *display text* only. If the cell wraps a
    # <w:hyperlink>, the link target lives in word/_rels/document.xml.rels (by
    # r:id) and is NOT changed here — the visible text and the click target can
    # diverge. Fine for plain-text cells; document this where hyperlinks matter.
    if not _set_runs_text(tc, text):
        raise ValueError("cell has no run text node to set")


def set_para_text(p, text):
    """Set a paragraph's text (first run), preserving its formatting. Returns
    False if the paragraph has no run to write into."""
    return _set_runs_text(p, text)
