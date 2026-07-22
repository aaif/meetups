"""Render a single slide of a Drive-hosted .pptx to PNG via the Slides API,
instead of a local LibreOffice conversion. LibreOffice substitutes local
system fonts for the deck's actual brand fonts, silently producing
wrong-looking exports; Google's own renderer (used here) does not.

Requires the `gws` CLI (Drive + Slides scopes) on PATH and authenticated.
"""
import json
import os
import subprocess
import time
import urllib.request

_SLIDES_MIME = "application/vnd.google-apps.presentation"

# Mirrors skills/aaif-create-chapter/scripts/create_chapter.py's _gws/gws_json —
# same retry list and empty/non-JSON-output guards, so a transient Drive/Slides
# hiccup here self-heals the same way it does for the rest of the toolkit.
_TRANSIENT = ("timed out", "internalError", "HTTP request failed",
              "Connection", "temporarily", "rateLimit", "userRateLimit",
              "backendError", "503", "500", "502")


def _gws(cmd, retries=5):
    for i in range(retries):
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode == 0:
            return r.stdout
        msg = (r.stderr or "") + (r.stdout or "")
        if i < retries - 1 and any(k in msg for k in _TRANSIENT):
            time.sleep(2 * (i + 1))
            continue
        raise RuntimeError("gws failed (%s): %s" % (r.returncode, msg.strip()[:400]))


def _gws_json(*args, params=None, body=None):
    cmd = ["gws", *args]
    if params is not None:
        cmd += ["--params", json.dumps(params)]
    if body is not None:
        cmd += ["--json", json.dumps(body)]
    out = _gws(cmd)
    s = "\n".join(l for l in out.split("\n") if "keyring backend" not in l).strip()
    if not s:
        raise RuntimeError("gws produced no JSON output for: %s" % " ".join(args))
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        raise RuntimeError("gws returned non-JSON output for %s: %s" % (" ".join(args), s[:200]))


def render_slide_png(file_id, out_path, slide_index=0, thumbnail_size="WIDTH2000_PX"):
    """Export slide `slide_index` (0-based) of the Drive pptx `file_id` to a PNG
    at `out_path`. Makes a throwaway Google Slides copy to render from (Slides
    thumbnails only work on native Slides files, not stored .pptx blobs) and
    trashes it afterward — the source file is never modified."""
    copy = _gws_json("drive", "files", "copy",
                      params={"fileId": file_id, "supportsAllDrives": True, "fields": "id"},
                      body={"name": "TEMP - render_slide_png", "mimeType": _SLIDES_MIME})
    presentation_id = copy["id"]
    try:
        presentation = _gws_json("slides", "presentations", "get",
                                  params={"presentationId": presentation_id, "fields": "slides.objectId"})
        page_object_id = presentation["slides"][slide_index]["objectId"]

        thumb = _gws_json("slides", "presentations", "pages", "getThumbnail",
                           params={"presentationId": presentation_id, "pageObjectId": page_object_id,
                                   "thumbnailProperties.thumbnailSize": thumbnail_size})
        os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
        urllib.request.urlretrieve(thumb["contentUrl"], out_path)
        if os.path.getsize(out_path) < 1000:
            raise RuntimeError("rendered thumbnail suspiciously small (%s)" % out_path)
        return out_path
    finally:
        try:
            _gws_json("drive", "files", "update", params={"fileId": presentation_id, "supportsAllDrives": True},
                      body={"trashed": True})
        except Exception:
            pass  # best-effort cleanup; a stray TEMP file is harmless clutter
