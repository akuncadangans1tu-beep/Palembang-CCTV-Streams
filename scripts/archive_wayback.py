#!/usr/bin/env python3
"""Kirim snapshot Wayback Machine + tulis ARCHIVE.md dengan daftar snapshot terbaru."""
import os, time, urllib.request, json
from datetime import datetime, timezone, timedelta

REPO = os.environ.get("GITHUB_REPOSITORY", "owner/repo")
UA = f"PalembangCCTV-archiver/1.0 (+https://github.com/{REPO})"
URLS = [
    ("Playlist", f"https://raw.githubusercontent.com/{REPO}/main/streams.m3u8"),
    ("Repo page", f"https://github.com/{REPO}"),
    ("status.json", f"https://raw.githubusercontent.com/{REPO}/main/status.json"),
]

def save(u):
    req = urllib.request.Request("https://web.archive.org/save/" + u, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            return r.status, r.geturl()
    except Exception as e:
        return None, f"{type(e).__name__}: {str(e)[:80]}"

def wib():
    return datetime.now(timezone(timedelta(hours=7))).strftime("%d %b %Y %H:%M WIB")

results = []
for label, u in URLS:
    st, info = save(u)
    results.append((label, u, st is not None, info))
    print(("OK  " if st else "SKIP"), label, "->", info)
    time.sleep(3)

# Tulis ARCHIVE.md
lines = [f"# 🗄️ Arsip Wayback Machine — {wib()}", "",
         "Snapshot otomatis dikirim mingguan ke Internet Archive. Klik tautan untuk melihat semua snapshot.", "",
         "| Label | URL | Status | Link Arsip |", "|---|---|:--:|---|"]
for label, u, ok, info in results:
    status = "✅" if ok else "❌"
    archive_url = f"https://web.archive.org/web/*/{u}"
    lines.append(f"| {label} | `{u}` | {status} | [lihat]({archive_url}) |")
lines += ["", "_Diperbarui otomatis setiap Senin 05:00 WIB oleh workflow `Visuals`._"]
from pathlib import Path
Path("ARCHIVE.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("[✓] ARCHIVE.md ditulis")
