#!/usr/bin/env python3
"""Snapshot critical AAIF ops data to local, versioned files.

Default target is the AAIF Community Intake Ops sheet. Pass a target to back up any
other file: a Google Drive fileId (native Docs/Sheets/Slides are exported to
.docx/.xlsx/.pptx; already-binary Drive files are downloaded as-is) or a local path
(copied verbatim).

Every run writes a NEW immutable file — nothing is ever overwritten:
    <dest>/<slug>/<UTC-timestamp>.<ext>
so the folder is a full version history you can diff or restore from. <dest> defaults
to ./backups (kept out of git); restore is manual (re-upload the .xlsx via gws).

Usage:
    backup.py                       # back up the Intake Ops sheet
    backup.py <driveFileId>         # back up any Drive file by id
    backup.py ./path/to/file.xlsx   # back up a local file
    backup.py --dest /some/dir      # write snapshots under a different root
"""
import argparse, datetime, json, os, re, shutil, subprocess, sys

# The one irreplaceable source of intake data — the default backup target.
INTAKE_OPS_ID = "1cWkjCI5AGK9RX_fs23P5jRA4I2nixgnHuapvwHseZ5o"

# Google-native mime type -> (export mime type, file extension).
EXPORT = {
    "application/vnd.google-apps.spreadsheet":
        ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "xlsx"),
    "application/vnd.google-apps.document":
        ("application/vnd.openxmlformats-officedocument.wordprocessingml.document", "docx"),
    "application/vnd.google-apps.presentation":
        ("application/vnd.openxmlformats-officedocument.presentationml.presentation", "pptx"),
}
# Binary mime type -> extension, for files downloaded via alt=media as-is.
BINARY_EXT = {
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": "pptx",
    "application/pdf": "pdf",
}


def gws_json(args):
    """Run a gws command expecting JSON on stdout (skips the keyring banner line)."""
    out = subprocess.run(["gws"] + args, capture_output=True, text=True)
    if out.returncode != 0:
        sys.exit(f"gws error: {' '.join(args[:4])}...\n{out.stderr.strip()}")
    txt = out.stdout
    i = txt.find("{")
    if i < 0:
        sys.exit(f"gws returned no JSON (got: {txt.strip()[:200]!r})")
    return json.loads(txt[i:])


def gws_download(args):
    """Run a gws command that writes bytes to --output; fail loudly on error."""
    out = subprocess.run(["gws"] + args, capture_output=True, text=True)
    if out.returncode != 0:
        sys.exit(f"gws error: {' '.join(args[:4])}...\n{out.stderr.strip()}")


def slugify(name):
    s = re.sub(r"[^\w.-]+", "-", name.strip()).strip("-.")
    return (s or "backup").lower()


def timestamp():
    # UTC, filename-safe, sorts chronologically. Second resolution is plenty.
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")


def snapshot_path(dest_root, slug, ext):
    d = os.path.join(dest_root, slug)
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, f"{timestamp()}.{ext}")


def backup_local(path, dest_root):
    if not os.path.isfile(path):
        sys.exit(f"ABORT: local file not found: {path}")
    base = os.path.basename(path)
    slug = slugify(os.path.splitext(base)[0])
    ext = base.rsplit(".", 1)[1] if "." in base else "bin"
    out = snapshot_path(dest_root, slug, ext)
    shutil.copy2(path, out)
    return out


def backup_drive(file_id, dest_root):
    meta = gws_json(["drive", "files", "get", "--params",
                     json.dumps({"fileId": file_id, "fields": "name,mimeType"}),
                     "--format", "json"])
    name, mime = meta.get("name", file_id), meta.get("mimeType", "")
    slug = slugify(name)
    if mime in EXPORT:
        export_mime, ext = EXPORT[mime]
        out = snapshot_path(dest_root, slug, ext)
        gws_download(["drive", "files", "export", "--params",
                      json.dumps({"fileId": file_id, "mimeType": export_mime}),
                      "--output", out])
    else:
        ext = BINARY_EXT.get(mime, "bin")
        out = snapshot_path(dest_root, slug, ext)
        gws_download(["drive", "files", "get", "--params",
                      json.dumps({"fileId": file_id, "alt": "media"}),
                      "--output", out])
    return out


def main():
    ap = argparse.ArgumentParser(description="Snapshot AAIF ops data to versioned files.")
    ap.add_argument("target", nargs="?",
                    help="Drive fileId or local path (default: Intake Ops sheet)")
    ap.add_argument("--dest", default=os.path.join(os.getcwd(), "backups"),
                    help="Root folder for snapshots (default: ./backups)")
    a = ap.parse_args()
    dest_root = os.path.abspath(a.dest)
    if a.target and os.path.exists(a.target):
        out = backup_local(a.target, dest_root)
    else:
        out = backup_drive(a.target or INTAKE_OPS_ID, dest_root)
    size = os.path.getsize(out)
    print(f"Backed up -> {out}  ({size:,} bytes)")


if __name__ == "__main__":
    main()
