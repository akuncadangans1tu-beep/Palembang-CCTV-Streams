#!/usr/bin/env python3
"""Thumbnail semua CCTV (kota + tol).
Strategi: resolve master->media->segmen lewat Python (SSL longgar + header),
lalu ffmpeg langsung ke segmen .ts (bypass HLS demuxer yang gagal di playlist bertoken pemkot).
Fallback: ffmpeg HLS biasa dengan -tls_verify 0."""
import re, ssl, subprocess, urllib.request
import concurrent.futures as cf
from pathlib import Path
from urllib.parse import urljoin

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
CTX = ssl.create_default_context(); CTX.check_hostname = False; CTX.verify_mode = ssl.CERT_NONE

def referer(u):
    return "https://cctv.palembang.go.id/" if "palembang.go.id" in u else "https://opencctv.org/"

def get(u):
    req = urllib.request.Request(u, headers={"User-Agent": UA, "Referer": referer(u), "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=15, context=CTX) as r:
        return r.read(300000).decode("utf-8", "ignore")

def lines(t):
    return [l.strip() for l in t.splitlines() if l.strip() and not l.strip().startswith("#")]

def resolve_segment(url):
    t = get(url)
    if "#EXTM3U" not in t: return None
    if "#EXT-X-STREAM-INF" in t:
        v = lines(t)
        if not v: return None
        url = urljoin(url, v[0]); t = get(url)
    s = lines(t)
    return urljoin(url, s[0]) if s else None

def parse(p):
    es = []; cur = None
    for l in Path(p).read_text(encoding="utf-8", errors="ignore").splitlines():
        l = l.strip()
        if not l: continue
        if l.startswith("#EXTINF:"):
            m = re.search(r'tvg-id="([^"]+)"', l); cur = m.group(1) if m else None
        elif not l.startswith("#"):
            if cur: es.append((cur, l))
            cur = None
    return es

def ffmpeg_frame(target, out, hdr):
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
           "-tls_verify", "0", "-headers", hdr,
           "-i", target, "-frames:v", "1", "-q:v", "4", "-vf", "scale=320:-2", str(out)]
    r = subprocess.run(cmd, timeout=30, capture_output=True)
    return r.returncode == 0 and out.exists() and out.stat().st_size > 0, r.stderr.decode("utf-8", "ignore")[:300]

def one(item):
    key, url = item
    out = Path("thumbs") / f"{key}.jpg"
    hdr = f"User-Agent: {UA}\r\nReferer: {referer(url)}\r\n"
    err = ""
    seg = None
    try: seg = resolve_segment(url)
    except Exception as e: err = f"resolve: {e}"
    targets = ([seg] if seg else []) + [url]
    for tgt in targets:
        ok, e = ffmpeg_frame(tgt, out, hdr)
        if ok: return (key, True, "")
        err = e or err
    return (key, False, err)

def main():
    Path("thumbs").mkdir(parents=True, exist_ok=True)
    es = parse("streams.m3u8")
    ok = 0; errs = []
    with cf.ThreadPoolExecutor(max_workers=6) as ex:
        for key, good, err in ex.map(one, es):
            if good: ok += 1
            elif len(errs) < 6: errs.append(f"{key}: {err}")
    for e in errs: print("[thumb-err]", e)
    print(f"[✓] thumbs {ok}/{len(es)}")

if __name__ == "__main__":
    main()
