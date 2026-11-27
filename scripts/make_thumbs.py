#!/usr/bin/env python3
"""Generate thumbnail semua CCTV (kota + tol) dengan ffmpeg.
Pakai -tls_verify 0 (server pemkot rantai sertifikatnya tidak dipercaya runner) + fallback.
Mencetak error asli bila gagal supaya mudah debug."""
import re, subprocess, concurrent.futures as cf
from pathlib import Path

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"

def referer(u):
    return "https://cctv.palembang.go.id/" if "palembang.go.id" in u else "https://opencctv.org/"

def parse(p):
    es = []; cur = None
    for l in Path(p).read_text(encoding="utf-8", errors="ignore").splitlines():
        l = l.strip()
        if not l: continue
        if l.startswith("#EXTINF:"):
            m = re.search(r'tvg-id="([^"]+)"', l)
            cur = m.group(1) if m else None
        elif not l.startswith("#"):
            if cur: es.append((cur, l))
            cur = None
    return es

def one(item):
    key, url = item
    out = Path("thumbs") / f"{key}.jpg"
    hdr = f"User-Agent: {UA}\r\nReferer: {referer(url)}\r\n"
    variants = [["-tls_verify", "0", "-headers", hdr],
                ["-headers", hdr],
                ["-tls_verify", "0"]]
    err = ""
    for extra in variants:
        cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", *extra,
               "-i", url, "-frames:v", "1", "-q:v", "4", "-vf", "scale=320:-2", str(out)]
        try:
            r = subprocess.run(cmd, timeout=30, capture_output=True)
            if r.returncode == 0 and out.exists() and out.stat().st_size > 0:
                return (key, True, "")
            err = r.stderr.decode("utf-8", "ignore")[:150]
        except Exception as e:
            err = str(e)[:150]
    return (key, False, err)

def main():
    Path("thumbs").mkdir(parents=True, exist_ok=True)
    es = parse("streams.m3u8")
    ok = 0; errs = []
    with cf.ThreadPoolExecutor(max_workers=6) as ex:
        for key, good, err in ex.map(one, es):
            if good: ok += 1
            elif len(errs) < 5: errs.append(f"{key}: {err}")
    for e in errs: print("[thumb-err]", e)
    print(f"[✓] thumbs {ok}/{len(es)}")

if __name__ == "__main__":
    main()
