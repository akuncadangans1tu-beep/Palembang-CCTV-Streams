#!/usr/bin/env python3
"""Cek URL .m3u8 di issue usulan + komentar otomatis. Hardened: tolak URL privat/invalid (SSRF)."""
import os, re, json, sys, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from update_streams import check, stable

TOKEN = os.environ.get("GITHUB_TOKEN")
REPO = os.environ.get("GITHUB_REPOSITORY", "owner/repo")
API = f"https://api.github.com/repos/{REPO}"
MARKER = "<!-- cctv-issue-check -->"

def gh(method, path, body=None):
    req = urllib.request.Request(API + path, data=json.dumps(body).encode() if body is not None else None,
        headers={"Authorization": f"Bearer {TOKEN}", "Accept": "application/vnd.github+json",
                 "User-Agent": "cctv-issue-check", "Content-Type": "application/json"}, method=method)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)

def main():
    if not TOKEN: print("[!] GITHUB_TOKEN tidak ada"); return 1
    issues = gh("GET", "/issues?state=open&per_page=100")
    n = 0
    for it in issues:
        if "pull_request" in it: continue
        labels = [l["name"] for l in it.get("labels", [])]
        if not (it["title"].startswith("[Usul Kamera]") or "kamera-baru" in labels): continue
        urls = re.findall(r'https?://[^\s"<>]+?\.m3u8[^\s"<>]*', it.get("body") or "")
        num = it["number"]
        if not urls: print(f"#{num}: tidak ada URL"); continue
        url = urls[0]
        if not stable(url):
            ok, reason = False, "URL diblokir (host privat/invalid/token)"
        else:
            ok, reason, _ = check(url)
        status = "LIVE" if ok else "GAGAL"
        comments = gh("GET", f"/issues/{num}/comments?per_page=100")
        prev = [c for c in comments if MARKER in (c.get("body") or "")]
        if prev and status in prev[-1]["body"]: continue
        msg = (f"{MARKER}\n🔍 **Cek otomatis:** {'✅ LIVE' if ok else '❌ GAGAL'} — `{url}`\nAlasan: {reason}\n\n"
               + ("Layak ditambahkan." if ok else "Perbaiki URL / pastikan aktif & publik."))
        gh("POST", f"/issues/{num}/comments", {"body": msg})
        print(f"#{num}: {status}"); n += 1
    print(f"[✓] {n} komentar baru")
    return 0

if __name__ == "__main__":
    sys.exit(main())
