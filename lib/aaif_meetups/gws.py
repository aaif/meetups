"""Shared Google Drive helpers, invoked through the `gws` CLI. Lifted from
create_chapter.py so every skill (chapter/series creation, event lifecycle)
uses one implementation. Stdlib-only."""
import json
import os
import subprocess
import time

PPTX = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
FOLDER = "application/vnd.google-apps.folder"
MIME_BY_EXT = {".pptx": PPTX, ".docx": DOCX, ".xlsx": XLSX}

_TRANSIENT = ("timed out", "internalError", "HTTP request failed",
              "Connection", "temporarily", "rateLimit", "userRateLimit",
              "backendError", "503", "500", "502")


def _gws(cmd, cwd=None, retries=5):
    """Run a gws command, retrying transient network/server errors."""
    for i in range(retries):
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
        if r.returncode == 0:
            return r.stdout
        msg = (r.stderr or "") + (r.stdout or "")
        if i < retries - 1 and any(k in msg for k in _TRANSIENT):
            time.sleep(2 * (i + 1))
            continue
        raise RuntimeError("gws failed (%s): %s" % (r.returncode, msg.strip()[:400]))


def gws_json(*args, params=None, body=None):
    cmd = ["gws", *args]
    if params is not None:
        cmd += ["--params", json.dumps(params)]
    if body is not None:
        cmd += ["--json", json.dumps(body)]
    out = _gws(cmd)
    s = "\n".join(l for l in out.splitlines() if "keyring backend" not in l).strip()
    if not s:
        # Empty-but-successful stdout would silently become {} -> an empty file
        # list -> a subtree that fails to clone while the run still says "Done".
        raise RuntimeError("gws produced no JSON output for: %s" % " ".join(args))
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        raise RuntimeError("gws returned non-JSON output for %s: %s" % (" ".join(args), s[:200]))


def gws_download(file_id, out):
    # gws rejects --output paths outside its cwd, so run it in the file's dir.
    d = os.path.dirname(out) or "."
    _gws(["gws", "drive", "files", "get", "--params",
          json.dumps({"fileId": file_id, "supportsAllDrives": True, "alt": "media"}),
          "--output", os.path.basename(out)], cwd=d)


def gws_upload(file_id, path, mime):
    d = os.path.dirname(path) or "."
    _gws(["gws", "drive", "files", "update", "--params",
          json.dumps({"fileId": file_id, "supportsAllDrives": True}),
          "--upload", os.path.basename(path), "--upload-content-type", mime], cwd=d)


def list_children(folder_id):
    res = gws_json("drive", "files", "list", params={
        "q": "'%s' in parents and trashed=false" % folder_id,
        "fields": "files(id,name,mimeType)", "pageSize": 1000,
        "supportsAllDrives": True, "includeItemsFromAllDrives": True})
    return res.get("files", [])


def find_child(folder_id, name):
    for c in list_children(folder_id):
        if c.get("name") == name:
            return c
    return None


def create_folder(name, parent):
    return gws_json("drive", "files", "create",
                    params={"supportsAllDrives": True},
                    body={"name": name, "mimeType": FOLDER, "parents": [parent]})["id"]


def copy_file(file_id, name, parent):
    return gws_json("drive", "files", "copy",
                    params={"fileId": file_id, "supportsAllDrives": True},
                    body={"name": name, "parents": [parent]})["id"]
