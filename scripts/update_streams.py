#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
update_streams.py — Cek, update, dan hapus link CCTV Palembang (.m3u8) otomatis.

Sumber:
  1. API resmi  : https://cctv.palembang.go.id/api/cctv
                  Stream  : https://cctv.palembang.go.id/api/cctv/{_id}/playback/index.m3u8
  2. OpenCCTV   : https://opencctv.org/cameras/indonesia/sumatera-selatan
                  https://opencctv.org/cameras/indonesia/south-sumatra
                  (kamera tol Palindra; URL .m3u8 diambil dari atribut player halaman kamera)

Alur: scrape sumber -> gabung dengan playlist lama -> cek semua link (HLS valid + segmen)
      -> update URL yang berubah -> hapus yang gagal N hari berturut-turut -> tulis ulang playlist.

Hanya butuh Python 3.9+ (tanpa pip install apa pun).
"""

import argparse
import concurrent.futures as cf
import html as htmlmod
import json
import re
import ssl
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

# ============================ KONFIGURASI ============================
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
PALEMBANG_API    = "https://cctv.palembang.go.id/api/cctv"
PALEMBANG_STREAM = "https://cctv.palembang.go.id/api/cctv/{id}/playback/index.m3u8"
OPENCCTV_REGIONS = [
    "https://opencctv.org/cameras/indonesia/sumatera-selatan",
    "https://opencctv.org/cameras/indonesia/south-sumatra",
]
DEFAULT_MAX_FAILS = 3     # link baru dihapus setelah gagal 3 hari berturut-turut
DEFAULT_TIMEOUT   = 12    # detik per request HTTP
DEFAULT_WORKERS   = 10    # cek paralel
# Beberapa server butuh context SSL longgar (rantai sertifikat tidak lengkap)
SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE
# =====================================================================


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def referer_for(url):
    if "palembang.go.id" in url:
        return "https://cctv.palembang.go.id/"
    return "https://opencctv.org/"


def http_get(url, timeout=DEFAULT_TIMEOUT, max_bytes=300000, retries=2):
    """GET sederhana dengan retry. Return (status_code, bytes)."""
    last_err = None
    for attempt in range(retries + 1):
        try:
            headers = {"User-Agent": UA, "Referer": referer_for(url), "Accept": "*/*"}
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout, context=SSL_CTX) as r:
                return r.status, r.read(max_bytes)
        except urllib.error.HTTPError as e:
            try:
                body = e.read(2048)
            except Exception:
                body = b""
            if e.code in (500, 502, 503, 504) and attempt < retries:
                last_err = e
                time.sleep(1.5 * (attempt + 1))
                continue
            return e.code, body
        except Exception as e:  # timeout, DNS, koneksi putus, SSL, dll.
            last_err = e
            if attempt < retries:
                time.sleep(1.5 * (attempt + 1))
    raise last_err if last_err else RuntimeError("gagal fetch " + url)


def first_uri_lines(text):
    return [l.strip() for l in text.splitlines()
            if l.strip() and not l.strip().startswith("#")]


def check_stream(url, timeout=DEFAULT_TIMEOUT):
    """Validasi HLS sungguhan: master -> media playlist -> segmen pertama.
    Return (ok: bool, alasan: str)."""
    try:
        st, body = http_get(url, timeout=timeout)
        if st != 200:
            return False, f"HTTP {st}"
        text = body.decode("utf-8", "ignore")
        if "#EXTM3U" not in text:
            return False, "bukan playlist M3U8"
        base = url
        # Master playlist? ikuti varian pertama.
        if "#EXT-X-STREAM-INF" in text:
            uris = first_uri_lines(text)
            if not uris:
                return False, "master tanpa varian"
            base = urljoin(url, uris[0])
            st, body = http_get(base, timeout=timeout)
            if st != 200:
                return False, f"varian HTTP {st}"
            text = body.decode("utf-8", "ignore")
            if "#EXTM3U" not in text:
                return False, "varian bukan M3U8"
        segs = first_uri_lines(text)
        if not segs:
            return False, "playlist tanpa segmen (stream mati)"
        # Cek segmen pertama benar-benar bisa diunduh (hemat: baca 2 KB saja)
        seg_url = urljoin(base, segs[0])
        st, _ = http_get(seg_url, timeout=timeout, max_bytes=2048, retries=1)
        if st not in (200, 206):
            return False, f"segmen HTTP {st}"
        return True, "OK"
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"[:120]


# ---------------------------- SCRAPER ----------------------------

def scrape_palembang(limit=None):
    """Ambil daftar kamera dari API resmi Diskominfo Palembang."""
    st, body = http_get(PALEMBANG_API)
    if st != 200:
        raise RuntimeError(f"API palembang HTTP {st}")
    data = json.loads(body.decode("utf-8", "ignore")).get("data", [])
    if not data:
        raise RuntimeError("API palembang trả về kosong / struktur berubah")
    out = []
    for cam in data:
        if cam.get("cctv_scope") != "publik" or cam.get("cctv_status") != "active":
            continue
        if not cam.get("playback_available"):
            continue
        cid = cam.get("cctv_id") or cam.get("_id")
        name = (cam.get("cctv_title") or cid).strip()
        opd = (cam.get("cctv_opd") or {}).get("nama_opd", "")
        if "Perhubungan" in opd:
            group = "Dishub Palembang"
        elif "Komunikasi" in opd:
            group = "Diskominfo Palembang"
        else:
            group = "Palembang"
        out.append({
            "key": f"plb-{cid}",
            "name": name,
            "group": group,
            "url": PALEMBANG_STREAM.format(id=cam["_id"]),
            "extra": [f"#EXTVLCOPT:http-user-agent={UA}",
                      "#EXTVLCOPT:http-referrer=https://cctv.palembang.go.id/"],
        })
        if limit and len(out) >= limit:
            break
    return out


def _opencctv_camera_links(region_url):
    """Kumpulkan link halaman kamera (termasuk paginasi) dari halaman region."""
    pages, seen_pages, links = [region_url], set(), set()
    while pages and len(seen_pages) < 6:
        page = pages.pop(0)
        if page in seen_pages:
            continue
        seen_pages.add(page)
        try:
            st, body = http_get(page)
        except Exception:
            continue
        if st != 200:
            continue
        html = body.decode("utf-8", "ignore")
        for href in re.findall(r'href="(/cameras/indonesia/[^"]+)"', html):
            full = "https://opencctv.org" + href
            if re.search(r"-\d+$", href) and href.count("/") >= 5:
                links.add(full)
            elif href.startswith(region_url.replace("https://opencctv.org", "")) and "?page=" in href:
                pages.append(full)
    return sorted(links)


def _extract_m3u8(html):
    for typ, src in re.findall(r'data-type="([^"]+)"[^>]*?data-src="([^"]+)"', html):
        if typ == "m3u8":
            return htmlmod.unescape(src)
    for src, typ in re.findall(r'data-src="([^"]+)"[^>]*?data-type="([^"]+)"', html):
        if typ == "m3u8":
            return htmlmod.unescape(src)
    m = re.search(r'https?://[^"\'\s]+\.m3u8[^"\'\s]*', html)
    return htmlmod.unescape(m.group(0)) if m else None


def _scrape_one_opencctv(link):
    try:
        st, body = http_get(link)
        if st != 200:
            return None
        html = body.decode("utf-8", "ignore")
        url = _extract_m3u8(html)
        if not url:
            return None
        cam_id = re.search(r"-(\d+)$", link).group(1)
        m = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.S)
        if m:
            name = re.sub(r"<[^>]+>", "", m.group(1))
            name = htmlmod.unescape(name).strip()
        else:
            slug = link.rsplit("/", 1)[-1]
            name = re.sub(r"-\d+$", "", slug).replace("-", " ").title()
        # Nama berupa penanda KM tol (mis. "01+600 A") -> beri prefix biar jelas
        if re.match(r"^[\d+\s]+[AB]?$", name):
            name = "Palindra " + name
        return {"key": f"oc-{cam_id}", "name": name, "group": "Tol Palindra",
                "url": url, "extra": []}
    except Exception:
        return None


def scrape_opencctv(limit=None, workers=DEFAULT_WORKERS):
    links = []
    for region in OPENCCTV_REGIONS:
        links.extend(_opencctv_camera_links(region))
    links = sorted(set(links))
    if not links:
        raise RuntimeError("tidak ada link kamera opencctv (situs down / struktur berubah)")
    if limit:
        links = links[:limit]
    out = []
    with cf.ThreadPoolExecutor(max_workers=workers) as ex:
        for res in ex.map(_scrape_one_opencctv, links):
            if res:
                out.append(res)
    if not out:
        raise RuntimeError("semua halaman kamera opencctv gagal di-scrape")
    return out


# ---------------------------- M3U ----------------------------

ATTR_RE = re.compile(r'([\w-]+)="([^"]*)"')


def parse_m3u(path):
    entries = []
    if not Path(path).exists():
        return entries
    lines = Path(path).read_text(encoding="utf-8", errors="ignore").splitlines()
    cur = None
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith("#EXTINF:"):
            attrs = dict(ATTR_RE.findall(line))
            name = line.split(",", 1)[1].strip() if "," in line else ""
            cur = {"attrs": attrs, "name": name, "extra": [], "url": None}
        elif line.startswith("#"):
            if cur is not None and not line.startswith("#EXTM3U"):
                cur["extra"].append(line)
        else:
            if cur is None:
                cur = {"attrs": {}, "name": line, "extra": [], "url": None}
            cur["url"] = line
            cur["key"] = cur["attrs"].get("tvg-id") or ("url:" + line)
            entries.append(cur)
            cur = None
    return entries


def entry_from_catalog(item):
    return {"attrs": {"tvg-id": item["key"], "group-title": item["group"]},
            "name": item["name"], "extra": list(item.get("extra", [])),
            "url": item["url"], "key": item["key"]}


def write_m3u(path, entries):
    lines = ["#EXTM3U"]
    for e in sorted(entries, key=lambda x: (x["attrs"].get("group-title", ""), x["name"].lower())):
        attrs = "".join(f' {k}="{v}"' for k, v in e["attrs"].items())
        lines.append(f"#EXTINF:-1{attrs},{e['name']}")
        lines.extend(e.get("extra", []))
        lines.append(e["url"])
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---------------------------- UTAMA ----------------------------

def main():
    ap = argparse.ArgumentParser(description="Cek/update/hapus stream CCTV Palembang")
    ap.add_argument("--playlist", default="palembang.m3u")
    ap.add_argument("--state", default="scripts/state.json")
    ap.add_argument("--max-fails", type=int, default=DEFAULT_MAX_FAILS)
    ap.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    ap.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    ap.add_argument("--limit", type=int, default=None, help="batasi jumlah kamera per sumber (untuk tes)")
    ap.add_argument("--skip-palembang", action="store_true")
    ap.add_argument("--skip-opencctv", action="store_true")
    ap.add_argument("--dry-run", action="store_true", help="jangan tulis file apa pun")
    args = ap.parse_args()

    state = {}
    if Path(args.state).exists():
        try:
            state = json.loads(Path(args.state).read_text(encoding="utf-8"))
        except Exception:
            state = {}

    entries = parse_m3u(args.playlist)
    by_key = {e["key"]: e for e in entries}
    print(f"[i] Playlist lama: {len(entries)} entri")

    # 1) Scrape sumber (kalau gagal, entri lama dari sumber itu DIPERTAHANKAN)
    catalog, source_ok = {}, {"palembang": False, "opencctv": False}
    if not args.skip_palembang:
        try:
            items = scrape_palembang(limit=args.limit)
            for it in items:
                catalog[it["key"]] = it
            source_ok["palembang"] = True
            print(f"[+] Sumber palembang.go.id: {len(items)} kamera")
        except Exception as e:
            print(f"[!] Gagal scrape palembang.go.id: {e} -> entri lama dipertahankan")
    if not args.skip_opencctv:
        try:
            items = scrape_opencctv(limit=args.limit, workers=args.workers)
            for it in items:
                catalog[it["key"]] = it
            source_ok["opencctv"] = True
            print(f"[+] Sumber opencctv.org: {len(items)} kamera")
        except Exception as e:
            print(f"[!] Gagal scrape opencctv.org: {e} -> entri lama dipertahankan")

    # 2) Merge: update URL/nama yang berubah, tambah kamera baru
    report, seen_urls = [], set()
    for key, item in catalog.items():
        if item["url"] in seen_urls:
            continue
        seen_urls.add(item["url"])
        if key in by_key:
            e = by_key[key]
            if e["url"] != item["url"]:
                report.append((e["name"], "UPDATED", f"URL diganti: {item['url']}"))
                e["url"] = item["url"]
            if e["name"] != item["name"]:
                e["name"] = item["name"]
            e["attrs"]["group-title"] = item["group"]
            e["extra"] = list(item.get("extra", []))
        else:
            e = entry_from_catalog(item)
            by_key[key] = e
            entries.append(e)
            report.append((e["name"], "NEW", "kamera baru dari sumber"))

    # 3) Tandai entri sumber yang hilang dari katalog (belum langsung dihapus)
    for e in entries:
        src = "palembang" if e["key"].startswith("plb-") else ("opencctv" if e["key"].startswith("oc-") else None)
        if src and source_ok[src] and e["key"] not in catalog:
            st = state.setdefault(e["key"], {"fail": 0, "missing": 0})
            st["missing"] = st.get("missing", 0) + 1
        elif src:
            state.setdefault(e["key"], {"fail": 0, "missing": 0})["missing"] = 0

    # 4) Cek semua link paralel
    print(f"[i] Mengecek {len(entries)} link (workers={args.workers}, timeout={args.timeout}s)...")
    results = {}
    with cf.ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(check_stream, e["url"], args.timeout): e for e in entries}
        for fut in cf.as_completed(futs):
            e = futs[fut]
            ok, reason = fut.result()
            results[e["key"]] = (ok, reason)
            print(f"    {'OK ' if ok else 'FAIL'} | {e['name']} | {reason}")

    # 5) Pengaman: kalau SEMUA gagal, kemungkinan IP runner diblokir / jaringan bermasalah.
    if len(entries) >= 5 and not any(ok for ok, _ in results.values()):
        print("[!!] SEMUA link gagal — kemungkinan masalah jaringan/geo-block.")
        print("[!!] Playlist & state TIDAK diubah supaya tidak terhapus massal.")
        return 0

    # 6) Hitung gagal beruntun, hapus yang lewat ambang
    kept, removed = [], []
    for e in entries:
        key = e["key"]
        st = state.setdefault(key, {"fail": 0, "missing": 0})
        ok, reason = results.get(key, (False, "tidak dicek"))
        st["last_check"] = now_iso()
        st["url"] = e["url"]
        if ok:
            st["fail"] = 0
            st["last_ok"] = st["last_check"]
            kept.append(e)
            continue
        st["fail"] = st.get("fail", 0) + 1
        is_new = any(n == e["name"] and s == "NEW" for n, s, _ in report)
        if is_new:
            removed.append((e, "baru tapi mati, dilewati"))
        elif st["fail"] >= args.max_fails:
            removed.append((e, f"gagal {st['fail']}x beruntun ({reason})"))
        elif st.get("missing", 0) >= args.max_fails:
            removed.append((e, f"hilang dari sumber {st['missing']} hari"))
        else:
            kept.append(e)
            report.append((e["name"], "FAIL", f"{reason} (gagal {st['fail']}/{args.max_fails})"))

    for e, why in removed:
        report.append((e["name"], "REMOVED", why))
        state.pop(e["key"], None)
        print(f"[-] HAPUS: {e['name']} — {why}")

    # 7) Tulis hasil
    summary = {"generated_at": now_iso(), "total": len(kept),
               "ok": sum(1 for ok, _ in results.values() if ok),
               "removed": len(removed),
               "sources": source_ok}
    print(f"[i] Ringkasan: {summary}")
    if args.dry_run:
        print("[i] DRY-RUN: tidak ada file yang ditulis.")
        return 0

    write_m3u(args.playlist, kept)
    Path(args.state).parent.mkdir(parents=True, exist_ok=True)
    Path(args.state).write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
    Path("status.json").write_text(json.dumps(
        {"summary": summary,
         "streams": [{"name": e["name"], "group": e["attrs"].get("group-title", ""),
                      "url": e["url"], "ok": results.get(e["key"], (False,))[0]} for e in kept]},
        indent=2, ensure_ascii=False), encoding="utf-8")
    md = [f"# Laporan Update Stream — {summary['generated_at']}", "",
          f"- Total aktif: **{summary['total']}** | OK: **{summary['ok']}** | Dihapus: **{summary['removed']}**", "",
          "| Nama | Status | Keterangan |", "|---|---|---|"]
    icon = {"NEW": "🆕", "UPDATED": "🔁", "FAIL": "⚠️", "REMOVED": "❌"}
    for name, status, note in report:
        md.append(f"| {name} | {icon.get(status, '')} {status} | {note} |")
    Path("REPORT.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"[✓] Selesai. {len(kept)} entri ditulis ke {args.playlist}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
