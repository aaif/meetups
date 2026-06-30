#!/usr/bin/env python3
"""Create a new AAIF city chapter by cloning the TemplateCity folder and
rebranding every Office file from "San Francisco" to the new city.

Two replacement tokens are swapped (event content like dates/speakers is left
untouched - organizers fill that per-event using the aaif-* content skills in
this repo, e.g. aaif-speaker-bio / aaif-announcement-post / aaif-dayof-slides):

  1. City name   "San Francisco" / "SAN FRANCISCO"  -> new city (case matched)
                 plus the "SF" abbreviation (AAIF SF, SF CHAPTER, ...) -> new
                 city, upper-cased in all-caps contexts and Title-cased in prose.
  2. Luma slug   aaif-sanfrancisco / aaif-sf         -> aaif-<newslug>

Usage:
  # Dry run - show what would happen, create nothing:
  python create_chapter.py --city "New York" --dry-run

  # Create the chapter in Drive:
  python create_chapter.py --city "New York"

  # Override the Luma slug (e.g. Denver's page lives at aaif-colorado):
  python create_chapter.py --city "Denver" --slug colorado

  # Test the text engine on a local folder of .pptx/.docx/.xlsx (no Drive):
  python create_chapter.py --city "Los Angeles" --rebrand-local ./somedir
"""
import argparse, html, os, pathlib, re, sys, unicodedata, urllib.error, urllib.request, zipfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
from aaif_meetups.gws_cli import (  # noqa: E402
    gws_download, gws_upload, list_children, create_folder, copy_file,
    FOLDER, MIME_BY_EXT,
)

CHAPTERS_PARENT = "1IQ1K7aVOKUUkxAcfLuNjdETEnmavvtjx"   # the "Chapters" Drive folder
TEMPLATE_FOLDER = "1PHvEgqnHo0RrsFyA47O9iRJGaKehC8Eg"   # the "TemplateCity" folder
SOURCE_NAME, SOURCE_UPPER = "San Francisco", "SAN FRANCISCO"

# ----------------------------------------------------------------------------
# Text rebranding engine (pure, unit-testable)
# ----------------------------------------------------------------------------
def slugify(city):
    s = unicodedata.normalize("NFKD", city).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]", "", s.lower())

def transform_text(text, name, upper, newslug):
    """Apply all city/slug replacements to one piece of *plain* text."""
    # 1. Luma slug (before the bare-SF pass, since it owns the '-SF' form)
    def luma(m):
        return ("AAIF-" + newslug.upper()) if m.group(0).isupper() else ("aaif-" + newslug)
    text = re.sub(r"(?i)aaif-(?:sanfrancisco|sf)\b", luma, text)
    # 2. Full city name
    text = text.replace(SOURCE_NAME, name).replace(SOURCE_UPPER, upper)
    # 3. Bare "SF" abbreviation - case decided by surrounding words
    def sf(m):
        after = text[m.end(): m.end() + 30]
        before = text[max(0, m.start() - 30): m.start()]
        nxt = re.search(r"[A-Za-z]{2,}", after)
        nxt = nxt.group(0) if nxt else ""
        prevs = re.findall(r"[A-Za-z]{2,}", before)
        prev = prevs[-1] if prevs else ""
        up = nxt.isupper() if nxt else (prev.isupper() if prev else False)
        return upper if up else name
    text = re.sub(r"\bSF\b", sf, text)
    return text

def _process_paragraphs(xml, ptag, ttag, tx):
    """Concatenate the text runs in each paragraph, transform, and write the
    result back into the first run (emptying the rest) so formatting and any
    run-splitting are preserved."""
    pre = re.compile(r"<%s\b[^>]*>.*?</%s>" % (re.escape(ptag), re.escape(ptag)), re.S)
    tre = re.compile(r"(<%s\b[^>]*>)(.*?)(</%s>)" % (re.escape(ttag), re.escape(ttag)), re.S)

    def do_para(pm):
        block = pm.group(0)
        runs = list(tre.finditer(block))
        if not runs:
            return block
        concat = "".join(html.unescape(r.group(2)) for r in runs)
        new = tx(concat)
        if new == concat:
            return block
        new_esc = html.escape(new, quote=False)
        out, last, first = [], 0, True
        for r in runs:
            out.append(block[last:r.start()])
            open_, _txt, close = r.group(1), r.group(2), r.group(3)
            if first:
                if "xml:space" not in open_:
                    open_ = open_[:-1] + ' xml:space="preserve">'
                out.append(open_ + new_esc + close)
                first = False
            else:
                out.append(open_ + close)
            last = r.end()
        out.append(block[last:])
        return "".join(out)

    return pre.sub(do_para, xml)

def rebrand_part(part_name, data, name, upper, newslug):
    """Return rebranded bytes for one OOXML part (or the original if unchanged)."""
    tx = lambda s: transform_text(s, name, upper, newslug)
    try:
        xml = data.decode("utf-8")
    except UnicodeDecodeError:
        return data
    if re.match(r"ppt/slides/slide\d+\.xml$", part_name):
        xml = _process_paragraphs(xml, "a:p", "a:t", tx)
    elif part_name == "word/document.xml":
        xml = _process_paragraphs(xml, "w:p", "w:t", tx)
    elif part_name == "xl/sharedStrings.xml":
        xml = _process_paragraphs(xml, "si", "t", tx)
    elif part_name in ("docProps/core.xml", "docProps/app.xml"):
        # metadata: chapter labelled "AAIF SF" -> "AAIF <UPPER>"
        xml = xml.replace("AAIF SF", "AAIF " + upper)
        xml = xml.replace(SOURCE_NAME, name).replace(SOURCE_UPPER, upper)
        xml = re.sub(r"(?i)aaif-(?:sanfrancisco|sf)\b",
                     lambda m: ("AAIF-" + newslug.upper()) if m.group(0).isupper() else ("aaif-" + newslug), xml)
    elif part_name.endswith(".rels"):
        # hyperlink targets to the Luma page
        xml = re.sub(r"(?i)aaif-(?:sanfrancisco|sf)\b",
                     lambda m: ("AAIF-" + newslug.upper()) if m.group(0).isupper() else ("aaif-" + newslug), xml)
    else:
        return data
    return xml.encode("utf-8")

def rebrand_file(path, name, upper, newslug):
    """Rewrite an .pptx/.docx/.xlsx in place. Returns number of parts changed."""
    tmp = path + ".new"
    zin = zipfile.ZipFile(path, "r")
    zout = zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED)
    changed = 0
    for it in zin.infolist():
        data = zin.read(it.filename)
        new = rebrand_part(it.filename, data, name, upper, newslug)
        if new != data:
            changed += 1
        zi = zipfile.ZipInfo(it.filename, date_time=it.date_time)
        zi.compress_type = it.compress_type
        zi.external_attr = it.external_attr
        zout.writestr(zi, new)
    zin.close(); zout.close()
    if zipfile.ZipFile(tmp).testzip() is not None:
        os.remove(tmp); raise RuntimeError("repackaged zip failed validation: " + path)
    os.replace(tmp, path)
    return changed

def residual_tokens(path):
    """List any stale San Francisco / SF / aaif-sf tokens still present."""
    z = zipfile.ZipFile(path); hits = []
    for n in z.namelist():
        if not n.endswith((".xml", ".rels")):
            continue
        d = z.read(n)
        for pat in (rb"San Francisco", rb"SAN FRANCISCO", rb"aaif-sf(?![a-z])", rb"\bSF\b"):
            if re.search(pat, d, re.I):
                hits.append((n.split("/")[-1], pat.decode("latin1")))
    return hits

# Drive helpers (_gws/gws_json/gws_download/gws_upload/list_children/create_folder/
# copy_file) now live in lib/aaif_meetups/gws_cli.py and are imported above.

def luma_status(slug):
    """Return 'live' (HTTP 200), 'absent' (HTTP 404), or 'unknown' (could not
    verify: timeout, DNS/SSL, 403/429/5xx). Never report a hard 404 for a
    failure we could not actually confirm."""
    # Luma rejects HEAD and bare urllib UAs with 403; use GET + a browser UA.
    req = urllib.request.Request("https://luma.com/aaif-" + slug, method="GET",
                                 headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return "live" if r.status == 200 else "unknown"
    except urllib.error.HTTPError as e:
        return "absent" if e.code == 404 else "unknown"
    except Exception:
        return "unknown"

# ----------------------------------------------------------------------------
def clone_and_rebrand(folder_id, parent, name, ctx, indent=""):
    """Recursively copy `folder_id` into `parent` as `name`, rebranding files."""
    new_id = create_folder(name, parent)
    print("%s+ %s/" % (indent, name))
    for child in list_children(folder_id):
        cname, cid, mime = child["name"], child["id"], child["mimeType"]
        if mime == FOLDER:
            clone_and_rebrand(cid, new_id, cname, ctx, indent + "  ")
        else:
            copy_id = copy_file(cid, cname, new_id)
            ext = os.path.splitext(cname)[1].lower()
            if ext in MIME_BY_EXT:
                tmp = os.path.join(ctx["tmp"], "f" + copy_id + ext)
                gws_download(copy_id, tmp)
                n = rebrand_file(tmp, ctx["name"], ctx["upper"], ctx["slug"])
                if n:
                    gws_upload(copy_id, tmp, MIME_BY_EXT[ext])
                left = residual_tokens(tmp)
                if left:
                    ctx["residuals"].append((cname, left))
                flag = "  !! residual %s" % left if left else ""
                print("%s  - %s (%d parts)%s" % (indent, cname, n, flag))
                os.remove(tmp)
            else:
                print("%s  - %s (copied)" % (indent, cname))
    return new_id

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--city", required=True, help='Full city name, e.g. "New York"')
    ap.add_argument("--slug", help="Luma slug override (default: city, lowercased, no spaces)")
    ap.add_argument("--dry-run", action="store_true", help="Plan only; create nothing")
    ap.add_argument("--rebrand-local", metavar="DIR",
                    help="Rebrand .pptx/.docx/.xlsx in a local dir (no Drive); for testing")
    a = ap.parse_args()

    name = a.city.strip()
    upper = name.upper()
    slug = a.slug.strip().lower() if a.slug else slugify(name)
    print("City : %s" % name)
    print("Upper: %s" % upper)
    print("Slug : aaif-%s  ->  https://luma.com/aaif-%s" % (slug, slug))

    if a.rebrand_local:
        residual_any = False
        for root, _d, files in os.walk(a.rebrand_local):
            for f in files:
                if os.path.splitext(f)[1].lower() in MIME_BY_EXT:
                    p = os.path.join(root, f)
                    n = rebrand_file(p, name, upper, slug)
                    left = residual_tokens(p)
                    if left:
                        residual_any = True
                    print("  %s: %d parts%s" % (f, n, ("  !! " + str(left)) if left else ""))
        if residual_any:
            sys.exit("FAIL: residual source tokens remain after rebrand (see !! above).")
        return

    status = luma_status(slug)
    print("Luma : %s" % {
        "live": "LIVE (200)",
        "absent": "NOT LIVE (404) - create the page at luma.com, or pass --slug",
        "unknown": "COULD NOT VERIFY - network error reaching luma.com; check aaif-%s manually" % slug,
    }[status])

    existing = [c for c in list_children(CHAPTERS_PARENT)
                if c["name"].lower() == name.lower() and c["mimeType"] == FOLDER]
    if existing:
        sys.exit("ABORT: a chapter folder named %r already exists (%s)" % (name, existing[0]["id"]))

    if a.dry_run:
        print("\n[dry-run] Would clone TemplateCity -> %r under Chapters and rebrand all files." % name)
        if status == "absent":
            print("[dry-run] WARNING: Luma page aaif-%s is not live yet." % slug)
        elif status == "unknown":
            print("[dry-run] NOTE: could not verify the Luma page aaif-%s; check it manually." % slug)
        return

    ctx = {"name": name, "upper": upper, "slug": slug, "residuals": [],
           "tmp": os.path.join(os.environ.get("TMPDIR", "/tmp"), "aaif_chapter")}
    os.makedirs(ctx["tmp"], exist_ok=True)
    print()
    new_id = clone_and_rebrand(TEMPLATE_FOLDER, CHAPTERS_PARENT, name, ctx)
    print("\nDone. New chapter folder id: %s" % new_id)
    print("https://drive.google.com/drive/folders/%s" % new_id)
    if status == "absent":
        print("REMINDER: create the Luma page at https://luma.com/aaif-%s (it is not live yet)." % slug)
    elif status == "unknown":
        print("REMINDER: could not verify the Luma page aaif-%s; check it manually at luma.com." % slug)
    if ctx["residuals"]:
        print("\nWARNING: %d file(s) still contain source tokens after rebrand:" % len(ctx["residuals"]))
        for fn, toks in ctx["residuals"]:
            print("  - %s: %s" % (fn, toks))
        sys.exit("The new folder is NOT clean - fix the template or rebrand engine and re-run.")

if __name__ == "__main__":
    main()
