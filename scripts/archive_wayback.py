#!/usr/bin/env python3
"""Kirim snapshot Wayback Machine (web.archive.org) untuk playlist & halaman repo.
Gratis, tanpa API key. Gagal tidak menggagalkan workflow."""
import os, time, urllib.request

REPO = os.environ.get("GITHUB_REPOSITORY", "owner/repo")
UA = f"PalembangCCTV-archiver/1.0 (+https://github.com/{REPO})"
URLS = [f"https://raw.githubusercontent.com/{REPO}/main/streams.m3u8",
        f"https://github.com/{REPO}",
        f"https://raw.githubusercontent.com/{REPO}/main/status.json"]

def save(u):
    req = urllib.request.Request("https://web.archive.org/save/" + u, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            return r.status, r.geturl()
    except Exception as e:
        return None, f"{type(e).__name__}: {str(e)[:80]}"

for u in URLS:
    st, info = save(u)
    print(("OK  " if st else "SKIP"), u, "->", info)
    time.sleep(3)
print("[✓] wayback selesai")
