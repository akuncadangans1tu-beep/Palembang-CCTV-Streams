#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
update_streams.py — Cek, update, hapus link CCTV Palembang & koridor Sumatera (.m3u8).
Menghasilkan: streams.m3u8, status.json (API mini + koordinat), history.json (uptime),
REPORT.md, dan tabel status di README.md. Hanya Python 3.9+ (tanpa pip install).
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
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import urljoin, urlsplit

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
PALEMBANG_API    = "https://cctv.palembang.go.id/api/cctv"
PALEMBANG_STREAM = "https://cctv.palembang.go.id/api/cctv/{id}/playback/index.m3u8"
OPENCCTV_REGIONS = [
    ("https://opencctv.org/cameras/indonesia/sumatera-selatan", "Tol Palindra", "Palindra "),
    ("https://opencctv.org/cameras/indonesia/lampung",          "Tol Lampung",  "Lampung "),
]
CORS_HOSTS = ("hk-opt.com",)   # host yang bisa diputar langsung di browser
DEFAULT_MAX_FAILS = 3
DEFAULT_TIMEOUT   = 12
DEFAULT_WORKERS   = 10
HISTORY_LEN       = 30
SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE
TOKEN_RE = re.compile(r"[?&](token|expires?|expiration|signature|sig|auth|hdnts|hdnea|policy|key-pair-id)=", re.I)
README_START = "<!-- STATUS:START -->"
README_END   = "<!-- STATUS:END -->"


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def wib_now():
    return datetime.now(timezone(timedelta(hours=7))).strftime("%d %b %Y %H:%M WIB")


def normalize_name(s):
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def referer_for(url):
    return "https://cctv.palembang.go.id/" if "palembang.go.id" in url else "https://opencctv.org/"


def web_playable(url):
    return any(h in urlsplit(url).netloc.lower() for h in CORS_HOSTS)


def is_stable_stream(url):
    if not url or not url.lower().startswith(("http://", "https://")):
        return False
    if "opencctv.org" in urlsplit(url).netloc.lower():
        return False
    if TOKEN_RE.search(url):
        return False
    return True


def http_get(url, timeout=DEFAULT_TIMEOUT, max_bytes=300000, retries=2):
    last_err = None
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Referer": referer_for(url), "Accept": "*/*"})
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
        except Exception as e:
            last_err = e
            if attempt < retries:
                time.sleep(1.5 * (attempt + 1))
    raise last_err if last_err else RuntimeError("gagal fetch " + url)


def first_uri_lines(text):
    return [l.strip() for l in text.splitlines() if l.strip() and not l.strip().startswith("#")]


def check_stream(url, timeout=DEFAULT_TIMEOUT):
    try:
        st, body = http_get(url, timeout=timeout)
        if st != 200:
            return False, f"HTTP {st}"
        text = body.decode("utf-8", "ignore")
        if "#EXTM3U" not in text:
            return False, "bukan playlist M3U8"
        base = url
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
        st, _ = http_get(urljoin(base, segs[0]), timeout=timeout, max_bytes=2048, retries=1)
        if st not in (200, 206):
            return False, f"segmen HTTP {st}"
        return True, "OK"
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"[:120]


def scrape_palembang(limit=None):
    st, body = http_get(PALEMBANG_API)
    if st != 200:
        raise RuntimeError(f"API palembang HTTP {st}")
    data = json.loads(body.decode("utf-8", "ignore")).get("data", [])
    if not data:
        raise RuntimeError("API palembang kosong / struktur berubah")
    out = []
    for cam in data:
        if cam.get("cctv_scope") != "publik" or cam.get("cctv_status") != "active":
            continue
        if not cam.get("playback_available"):
            continue
        cid = cam.get("cctv_id") or cam.get("_id")
        name = (cam.get("cctv_title") or cid).strip()
        opd = (cam.get("cctv_opd") or {}).get("nama_opd", "")
        group = "Dishub Palembang" if "Perhubungan" in opd else ("Diskominfo Palembang" if "Komunikasi" in opd else "Palembang")
        lat = lng = None
        coords = (cam.get("location") or {}).get("coordinates") or []
        if len(coords) >= 2:
            lng, lat = coords[0], coords[1]
        out.append({"key": f"plb-{cid}", "name": name, "group": group,
                    "url": PALEMBANG_STREAM.format(id=cam["_id"]),
                    "lat": lat, "lng": lng, "web": False,
                    "extra": [f"#EXTVLCOPT:http-user-agent={UA}",
                              "#EXTVLCOPT:http-referrer=https://cctv.palembang.go.id/"]})
        if limit and len(out) >= limit:
            break
    return out


def _opencctv_camera_links(region_url):
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
    cands = []
    for typ, src in re.findall(r'data-type="([^"]+)"[^>]*?data-src="([^"]+)"', html):
        if typ == "m3u8":
            cands.append(htmlmod.unescape(src))
    for src, typ in re.findall(r'data-src="([^"]+)"[^>]*?data-type="([^"]+)"', html):
        if typ == "m3u8":
            cands.append(htmlmod.unescape(src))
    cands += [htmlmod.unescape(m.group(0)) for m in re.finditer(r'https?://[^"\'\s]+\.m3u8[^"\'\s]*', html)]
    for u in cands:
        if is_stable_stream(u):
            return u
    return None


def _scrape_one_opencctv(link, group, prefix):
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
            name = htmlmod.unescape(re.sub(r"<[^>]+>", "", m.group(1))).strip()
        else:
            name = re.sub(r"-\d+$", "", link.rsplit("/", 1)[-1]).replace("-", " ").title()
        if re.match(r"^[\d+\s]+[AB]?$", name):
            name = prefix + name
        lat = lng = None
        mlat = re.search(r'data-lat="([-\d.]+)"', html)
        mlng = re.search(r'data-lng="([-\d.]+)"', html)
        if mlat and mlng:
            lat, lng = float(mlat.group(1)), float(mlng.group(1))
        return {"key": f"oc-{cam_id}", "name": name, "group": group, "url": url,
                "lat": lat, "lng": lng, "web": web_playable(url), "extra": []}
    except Exception:
        return None


def scrape_opencctv(limit=None, workers=DEFAULT_WORKERS):
    jobs, seen = [], set()
    for region_url, group, prefix in OPENCCTV_REGIONS:
        for link in _opencctv_camera_links(region_url):
            if link not in seen:
                seen.add(link)
                jobs.append((link, group, prefix))
    if not jobs:
        raise RuntimeError("tidak ada link kamera opencctv")
    if limit:
        jobs = jobs[:limit]
    out = []
    with cf.ThreadPoolExecutor(max_workers=workers) as ex:
        futs = [ex.submit(_scrape_one_opencctv, l, g, p) for l, g, p in jobs]
        for fut in cf.as_completed(futs):
            res = fut.result()
            if res:
                out.append(res)
    if not out:
        raise RuntimeError("tidak ada stream stabil dari opencctv")
    return out


ATTR_RE = re.compile(r'([\w-]+)="([^"]*)"')


def parse_m3u(path):
    entries = []
    if not Path(path).exists():
        return entries
    cur = None
    for line in Path(path).read_text(encoding="utf-8", errors="ignore").splitlines():
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
            "url": item["url"], "key": item["key"],
            "lat": item.get("lat"), "lng": item.get("lng"),
            "web": item.get("web", web_playable(item["url"]))}


def write_m3u(path, entries):
    lines = ["#EXTM3U"]
    for e in sorted(entries, key=lambda x: (x["attrs"].get("group-title", ""), x["name"].lower())):
        attrs = "".join(f' {k}="{v}"' for k, v in e["attrs"].items())
        lines.append(f"#EXTINF:-1{attrs},{e['name']}")
        lines.extend(e.get("extra", []))
        lines.append(e["url"])
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def merge_catalog(entries, catalog):
    report = []
    by_key = {e["key"]: e for e in entries}
    by_url, by_name = {}, {}
    for e in entries:
        if not e["attrs"].get("tvg-id"):
            by_url.setdefault(e["url"], e)
            by_name.setdefault(normalize_name(e["name"]), e)

    def sync(e, item):
        e["attrs"]["group-title"] = item["group"]
        e["extra"] = list(item.get("extra", []))
        e["lat"], e["lng"] = item.get("lat"), item.get("lng")
        e["web"] = item.get("web", web_playable(item["url"]))

    seen_urls = set()
    for key, item in catalog.items():
        if item["url"] in seen_urls:
            continue
        seen_urls.add(item["url"])
        e = by_key.get(key)
        if e is not None:
            if e["url"] != item["url"]:
                report.append((e["name"], "UPDATED", f"URL diganti ke {item['url']}"))
                e["url"] = item["url"]
            sync(e, item)
            continue
        e = by_url.pop(item["url"], None)
        if e is not None:
            by_name.pop(normalize_name(e["name"]), None)
            e["key"] = key
            e["attrs"]["tvg-id"] = key
            sync(e, item)
            by_key[key] = e
            report.append((e["name"], "ADOPTED", f"link lama = '{item['name']}' ({key})"))
            continue
        e = by_name.pop(normalize_name(item["name"]), None)
        if e is not None:
            by_url.pop(e["url"], None)
            old = e["url"]
            e["key"] = key
            e["url"] = item["url"]
            e["attrs"]["tvg-id"] = key
            sync(e, item)
            by_key[key] = e
            report.append((e["name"], "MIGRATED", f"{old} -> {item['url']}"))
            continue
        e = entry_from_catalog(item)
        by_key[key] = e
        entries.append(e)
        report.append((e["name"], "NEW", "kamera baru dari sumber"))
    return report


def dedup_urls(entries):
    seen, kept, removed = {}, [], []
    for e in entries:
        if e["url"] in seen:
            removed.append((e, f"duplikat URL dengan '{seen[e['url']]}'"))
            continue
        seen[e["url"]] = e["name"]
        kept.append(e)
    return kept, removed


def load_history(path):
    if Path(path).exists():
        try:
            return json.loads(Path(path).read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def update_history(history, kept, results):
    for e in kept:
        ok = results.get(e["key"], (False, ""))[0]
        h = history.setdefault(e["key"], {"total": 0, "ok": 0, "recent": []})
        h["total"] += 1
        h["ok"] += 1 if ok else 0
        h["recent"] = (h.get("recent", []) + [bool(ok)])[-HISTORY_LEN:]
        h["uptime_pct"] = round(100.0 * h["ok"] / h["total"]) if h["total"] else 0
    return history


def build_status_block(kept, results, history):
    live = sum(1 for e in kept if results.get(e["key"], (False, ""))[0])
    off = len(kept) - live
    lines = [f"> 🕒 Diperbarui: **{wib_now()}** · Total **{len(kept)}** · 🟢 **{live}** live · 🔴 **{off}** offline",
             "", "| Kamera | Grup | Status | Uptime |", "|---|---|:--:|:--:|"]
    for e in sorted(kept, key=lambda x: (x["attrs"].get("group-title", ""), x["name"].lower())):
        ok = results.get(e["key"], (False, ""))[0]
        up = history.get(e["key"], {}).get("uptime_pct", 100 if ok else 0)
        name = e["name"].replace("|", "\\|")
        group = e["attrs"].get("group-title", "").replace("|", "\\|")
        lines.append(f"| {name} | {group} | {'🟢 Live' if ok else '🔴 Offline'} | {up}% |")
    lines += ["", "_🔴 Offline = gagal cek terakhir; dipertahankan maks 3 hari berturut-turut sebelum dihapus._"]
    return "\n".join(lines)


def update_readme(path, kept, results, history):
    p = Path(path)
    if not p.exists():
        return False
    text = p.read_text(encoding="utf-8")
    if README_START not in text or README_END not in text:
        return False
    block = build_status_block(kept, results, history)
    pre = text.split(README_START, 1)[0]
    post = text.split(README_END, 1)[1]
    p.write_text(pre + README_START + "\n" + block + "\n" + README_END + post, encoding="utf-8")
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--playlist", default="streams.m3u8")
    ap.add_argument("--state", default="scripts/state.json")
    ap.add_argument("--history", default="history.json")
    ap.add_argument("--max-fails", type=int, default=DEFAULT_MAX_FAILS)
    ap.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    ap.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--skip-palembang", action="store_true")
    ap.add_argument("--skip-opencctv", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    state = {}
    if Path(args.state).exists():
        try:
            state = json.loads(Path(args.state).read_text(encoding="utf-8"))
        except Exception:
            state = {}
    history = load_history(args.history)

    entries = parse_m3u(args.playlist)
    print(f"[i] Playlist lama: {len(entries)} entri")
    catalog, source_ok = {}, {"palembang": False, "opencctv": False}
    if not args.skip_palembang:
        try:
            items = scrape_palembang(limit=args.limit)
            for it in items:
                catalog[it["key"]] = it
            source_ok["palembang"] = True
            print(f"[+] palembang.go.id: {len(items)} kamera")
        except Exception as e:
            print(f"[!] Gagal scrape palembang: {e}")
    if not args.skip_opencctv:
        try:
            items = scrape_opencctv(limit=args.limit, workers=args.workers)
            for it in items:
                catalog[it["key"]] = it
            source_ok["opencctv"] = True
            print(f"[+] opencctv (stabil): {len(items)} kamera")
        except Exception as e:
            print(f"[!] Gagal scrape opencctv: {e}")

    report = merge_catalog(entries, catalog)
    entries, dup_removed = dedup_urls(entries)
    for e, why in dup_removed:
        report.append((e["name"], "REMOVED", why))
        state.pop(e["key"], None)
        history.pop(e["key"], None)
        print(f"[-] HAPUS: {e['name']} — {why}")

    for e in entries:
        src = "palembang" if e["key"].startswith("plb-") else ("opencctv" if e["key"].startswith("oc-") else None)
        if src and source_ok[src] and e["key"] not in catalog:
            st = state.setdefault(e["key"], {"fail": 0, "missing": 0})
            st["missing"] = st.get("missing", 0) + 1
        elif src:
            state.setdefault(e["key"], {"fail": 0, "missing": 0})["missing"] = 0

    print(f"[i] Mengecek {len(entries)} link...")
    results = {}
    with cf.ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(check_stream, e["url"], args.timeout): e for e in entries}
        for fut in cf.as_completed(futs):
            e = futs[fut]
            ok, reason = fut.result()
            results[e["key"]] = (ok, reason)
            print(f"    {'OK ' if ok else 'FAIL'} | {e['name']} | {reason}")

    if len(entries) >= 5 and not any(ok for ok, _ in results.values()):
        print("[!!] SEMUA gagal — kemungkinan geo-block/jaringan. Tidak ada perubahan.")
        return 0

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
        history.pop(e["key"], None)
        print(f"[-] HAPUS: {e['name']} — {why}")

    history = update_history(history, kept, results)
    live = sum(1 for e in kept if results.get(e["key"], (False, ""))[0])
    summary = {"generated_at": now_iso(), "generated_wib": wib_now(),
               "total": len(kept), "live": live, "offline": len(kept) - live,
               "removed": len(removed) + len(dup_removed), "sources": source_ok}
    print(f"[i] Ringkasan: {summary}")
    if args.dry_run:
        print("[i] DRY-RUN: tidak menulis file.")
        return 0

    write_m3u(args.playlist, kept)
    Path(args.state).parent.mkdir(parents=True, exist_ok=True)
    Path(args.state).write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
    Path(args.history).write_text(json.dumps(history, indent=2, ensure_ascii=False), encoding="utf-8")
    streams = [{"key": e["key"], "name": e["name"], "group": e["attrs"].get("group-title", ""),
                "url": e["url"], "ok": results.get(e["key"], (False, ""))[0],
                "lat": e.get("lat"), "lng": e.get("lng"),
                "web": e.get("web", web_playable(e["url"])),
                "uptime_pct": history.get(e["key"], {}).get("uptime_pct", 100)} for e in kept]
    Path("status.json").write_text(json.dumps({"summary": summary, "streams": streams}, indent=2, ensure_ascii=False), encoding="utf-8")
    md = [f"# Laporan Update Stream — {summary['generated_at']}", "",
          f"- Total: **{summary['total']}** | Live: **{summary['live']}** | Offline: **{summary['offline']}** | Dihapus: **{summary['removed']}**", "",
          "| Nama | Status | Keterangan |", "|---|---|---|"]
    icon = {"NEW": "🆕", "UPDATED": "🔁", "ADOPTED": "🔗", "MIGRATED": "🔁", "FAIL": "⚠️", "REMOVED": "❌"}
    for name, status, note in report:
        md.append(f"| {name} | {icon.get(status, '')} {status} | {note} |")
    Path("REPORT.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    if update_readme("README.md", kept, results, history):
        print("[✓] README.md diperbarui.")
    print(f"[✓] Selesai. {len(kept)} entri -> {args.playlist}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
