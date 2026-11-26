#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
update_streams.py — CCTV Palembang & koridor Sumatera.
Output: streams.m3u8/.m3u + playlist pecahan, status.json, history.json, data/uptime.csv,
CHANGELOG.md, REPORT.md, removed.json, tabel README, dan (mode --thumbs) thumbs/*.jpg.
Hanya Python 3.9+; mode --thumbs butuh ffmpeg (tersedia di runner GitHub).
"""
import argparse
import concurrent.futures as cf
import csv
import html as htmlmod
import json
import re
import ssl
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import urljoin, urlsplit

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
RAW_BASE = "https://raw.githubusercontent.com/akuncadangans1tu-beep/Palembang-CCTV-Streams/main"
PALEMBANG_API    = "https://cctv.palembang.go.id/api/cctv"
PALEMBANG_STREAM = "https://cctv.palembang.go.id/api/cctv/{id}/playback/index.m3u8"
OPENCCTV_REGIONS = [
    ("https://opencctv.org/cameras/indonesia/sumatera-selatan", "Tol Palindra", "Palindra "),
    ("https://opencctv.org/cameras/indonesia/lampung",          "Tol Lampung",  "Lampung "),
    # Kandidat sumber baru (BELUM diverifikasi stabil — aktifkan setelah dicek):
    # ("https://opencctv.org/cameras/indonesia/banten",         "Tol Merak",    "Merak "),
    # ("https://opencctv.org/cameras/indonesia/sumatera-utara", "Tol Sumut",    "Sumut "),
]
CORS_HOSTS = ("hk-opt.com",)
DEFAULT_MAX_FAILS = 3
DEFAULT_TIMEOUT   = 12
DEFAULT_WORKERS   = 10
HISTORY_LEN       = 30
SSL_CTX = ssl.create_default_context(); SSL_CTX.check_hostname = False; SSL_CTX.verify_mode = ssl.CERT_NONE
TOKEN_RE = re.compile(r"[?&](token|expires?|expiration|signature|sig|auth|hdnts|hdnea|policy|key-pair-id)=", re.I)
README_START = "<!-- STATUS:START -->"; README_END = "<!-- STATUS:END -->"


def now_iso(): return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
def wib_now(): return datetime.now(timezone(timedelta(hours=7))).strftime("%d %b %Y %H:%M WIB")
def normalize_name(s): return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()
def referer_for(url): return "https://cctv.palembang.go.id/" if "palembang.go.id" in url else "https://opencctv.org/"
def web_playable(url): return any(h in urlsplit(url).netloc.lower() for h in CORS_HOSTS)
def logo_for(key): return f"{RAW_BASE}/thumbs/{key}.jpg"


def is_stable_stream(url):
    if not url or not url.lower().startswith(("http://", "https://")): return False
    if "opencctv.org" in urlsplit(url).netloc.lower(): return False
    if TOKEN_RE.search(url): return False
    return True


def http_get(url, timeout=DEFAULT_TIMEOUT, max_bytes=300000, retries=2):
    last = None
    for a in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Referer": referer_for(url), "Accept": "*/*"})
            with urllib.request.urlopen(req, timeout=timeout, context=SSL_CTX) as r:
                return r.status, r.read(max_bytes)
        except urllib.error.HTTPError as e:
            try: body = e.read(2048)
            except Exception: body = b""
            if e.code in (500, 502, 503, 504) and a < retries:
                last = e; time.sleep(1.5 * (a + 1)); continue
            return e.code, body
        except Exception as e:
            last = e
            if a < retries: time.sleep(1.5 * (a + 1))
    raise last if last else RuntimeError("gagal fetch " + url)


def first_uri_lines(t): return [l.strip() for l in t.splitlines() if l.strip() and not l.strip().startswith("#")]


def check_stream(url, timeout=DEFAULT_TIMEOUT):
    meta = {}
    try:
        st, body = http_get(url, timeout=timeout)
        if st != 200: return False, f"HTTP {st}", meta
        text = body.decode("utf-8", "ignore")
        if "#EXTM3U" not in text: return False, "bukan playlist M3U8", meta
        base = url
        if "#EXT-X-STREAM-INF" in text:
            res, bw = None, 0
            for line in text.splitlines():
                if line.startswith("#EXT-X-STREAM-INF"):
                    mr = re.search(r"RESOLUTION=(\d+x\d+)", line); mb = re.search(r"BANDWIDTH=(\d+)", line)
                    bb = int(mb.group(1)) if mb else 0
                    if bb >= bw: bw = bb; res = mr.group(1) if mr else res
            meta = {"resolution": res, "bandwidth_kbps": round(bw / 1000) if bw else None}
            uris = first_uri_lines(text)
            if not uris: return False, "master tanpa varian", meta
            base = urljoin(url, uris[0])
            st, body = http_get(base, timeout=timeout)
            if st != 200: return False, f"varian HTTP {st}", meta
            text = body.decode("utf-8", "ignore")
            if "#EXTM3U" not in text: return False, "varian bukan M3U8", meta
        segs = first_uri_lines(text)
        if not segs: return False, "playlist tanpa segmen (stream mati)", meta
        st, _ = http_get(urljoin(base, segs[0]), timeout=timeout, max_bytes=2048, retries=1)
        if st not in (200, 206): return False, f"segmen HTTP {st}", meta
        return True, "OK", meta
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"[:120], meta


def scrape_palembang(limit=None):
    st, body = http_get(PALEMBANG_API)
    if st != 200: raise RuntimeError(f"API palembang HTTP {st}")
    data = json.loads(body.decode("utf-8", "ignore")).get("data", [])
    if not data: raise RuntimeError("API palembang kosong / struktur berubah")
    out = []
    for cam in data:
        if cam.get("cctv_scope") != "publik" or cam.get("cctv_status") != "active": continue
        if not cam.get("playback_available"): continue
        cid = cam.get("cctv_id") or cam.get("_id")
        name = (cam.get("cctv_title") or cid).strip()
        kec = (cam.get("kecamatan") or {}).get("namaKecamatan", "")
        opd = (cam.get("cctv_opd") or {}).get("nama_opd", "")
        group = kec.title() if kec else ("Dishub Palembang" if "Perhubungan" in opd else "Diskominfo Palembang")
        lat = lng = None
        coords = (cam.get("location") or {}).get("coordinates") or []
        if len(coords) >= 2: lng, lat = coords[0], coords[1]
        out.append({"key": f"plb-{cid}", "name": name, "group": group,
                    "url": PALEMBANG_STREAM.format(id=cam["_id"]), "lat": lat, "lng": lng, "web": False,
                    "extra": [f"#EXTVLCOPT:http-user-agent={UA}", "#EXTVLCOPT:http-referrer=https://cctv.palembang.go.id/"]})
        if limit and len(out) >= limit: break
    return out


def _opencctv_camera_links(region_url):
    pages, seen, links = [region_url], set(), set()
    while pages and len(seen) < 6:
        p = pages.pop(0)
        if p in seen: continue
        seen.add(p)
        try: st, body = http_get(p)
        except Exception: continue
        if st != 200: continue
        html = body.decode("utf-8", "ignore")
        for href in re.findall(r'href="(/cameras/indonesia/[^"]+)"', html):
            full = "https://opencctv.org" + href
            if re.search(r"-\d+$", href) and href.count("/") >= 5: links.add(full)
            elif href.startswith(region_url.replace("https://opencctv.org", "")) and "?page=" in href: pages.append(full)
    return sorted(links)


def _extract_m3u8(html):
    c = []
    for typ, src in re.findall(r'data-type="([^"]+)"[^>]*?data-src="([^"]+)"', html):
        if typ == "m3u8": c.append(htmlmod.unescape(src))
    for src, typ in re.findall(r'data-src="([^"]+)"[^>]*?data-type="([^"]+)"', html):
        if typ == "m3u8": c.append(htmlmod.unescape(src))
    c += [htmlmod.unescape(m.group(0)) for m in re.finditer(r'https?://[^"\'\s]+\.m3u8[^"\'\s]*', html)]
    for u in c:
        if is_stable_stream(u): return u
    return None


def _scrape_one_opencctv(link, group, prefix):
    try:
        st, body = http_get(link)
        if st != 200: return None
        html = body.decode("utf-8", "ignore")
        url = _extract_m3u8(html)
        if not url: return None
        cam_id = re.search(r"-(\d+)$", link).group(1)
        m = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.S)
        name = htmlmod.unescape(re.sub(r"<[^>]+>", "", m.group(1))).strip() if m else re.sub(r"-\d+$", "", link.rsplit("/", 1)[-1]).replace("-", " ").title()
        if re.match(r"^[\d+\s]+[AB]?$", name): name = prefix + name
        lat = lng = None
        ml, mn = re.search(r'data-lat="([-\d.]+)"', html), re.search(r'data-lng="([-\d.]+)"', html)
        if ml and mn: lat, lng = float(ml.group(1)), float(mn.group(1))
        return {"key": f"oc-{cam_id}", "name": name, "group": group, "url": url, "lat": lat, "lng": lng, "web": web_playable(url), "extra": []}
    except Exception:
        return None


def scrape_opencctv(limit=None, workers=DEFAULT_WORKERS):
    jobs, seen = [], set()
    for ru, g, p in OPENCCTV_REGIONS:
        for l in _opencctv_camera_links(ru):
            if l not in seen: seen.add(l); jobs.append((l, g, p))
    if not jobs: raise RuntimeError("tidak ada link kamera opencctv")
    if limit: jobs = jobs[:limit]
    out = []
    with cf.ThreadPoolExecutor(max_workers=workers) as ex:
        for fut in cf.as_completed([ex.submit(_scrape_one_opencctv, l, g, p) for l, g, p in jobs]):
            r = fut.result()
            if r: out.append(r)
    if not out: raise RuntimeError("tidak ada stream stabil dari opencctv")
    return out


ATTR_RE = re.compile(r'([\w-]+)="([^"]*)"')


def parse_m3u(path):
    entries = []
    if not Path(path).exists(): return entries
    cur = None
    for line in Path(path).read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line: continue
        if line.startswith("#EXTINF:"):
            attrs = dict(ATTR_RE.findall(line)); name = line.split(",", 1)[1].strip() if "," in line else ""
            cur = {"attrs": attrs, "name": name, "extra": [], "url": None}
        elif line.startswith("#"):
            if cur is not None and not line.startswith("#EXTM3U"): cur["extra"].append(line)
        else:
            if cur is None: cur = {"attrs": {}, "name": line, "extra": [], "url": None}
            cur["url"] = line; cur["key"] = cur["attrs"].get("tvg-id") or ("url:" + line)
            entries.append(cur); cur = None
    return entries


def entry_from_catalog(item):
    return {"attrs": {"tvg-id": item["key"], "tvg-logo": logo_for(item["key"]), "group-title": item["group"]},
            "name": item["name"], "extra": list(item.get("extra", [])), "url": item["url"], "key": item["key"],
            "lat": item.get("lat"), "lng": item.get("lng"), "web": item.get("web", web_playable(item["url"]))}


def write_m3u(path, entries):
    lines = ["#EXTM3U"]
    for e in sorted(entries, key=lambda x: (x["attrs"].get("group-title", ""), x["name"].lower())):
        attrs = "".join(f' {k}="{v}"' for k, v in e["attrs"].items())
        lines.append(f"#EXTINF:-1{attrs},{e['name']}"); lines.extend(e.get("extra", [])); lines.append(e["url"])
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def merge_catalog(entries, catalog):
    report = []; by_key = {e["key"]: e for e in entries}; by_url, by_name = {}, {}
    for e in entries:
        if not e["attrs"].get("tvg-id"):
            by_url.setdefault(e["url"], e); by_name.setdefault(normalize_name(e["name"]), e)

    def sync(e, item):
        e["attrs"]["group-title"] = item["group"]; e["attrs"]["tvg-logo"] = logo_for(item["key"])
        e["extra"] = list(item.get("extra", [])); e["lat"], e["lng"] = item.get("lat"), item.get("lng")
        e["web"] = item.get("web", web_playable(item["url"]))

    seen = set()
    for key, item in catalog.items():
        if item["url"] in seen: continue
        seen.add(item["url"]); e = by_key.get(key)
        if e is not None:
            if e["url"] != item["url"]:
                report.append((e["name"], "UPDATED", f"URL diganti ke {item['url']}")); e["url"] = item["url"]
            sync(e, item); continue
        e = by_url.pop(item["url"], None)
        if e is not None:
            by_name.pop(normalize_name(e["name"]), None); e["key"] = key; e["attrs"]["tvg-id"] = key
            sync(e, item); by_key[key] = e
            report.append((e["name"], "ADOPTED", f"link lama = '{item['name']}' ({key})")); continue
        e = by_name.pop(normalize_name(item["name"]), None)
        if e is not None:
            by_url.pop(e["url"], None); old = e["url"]; e["key"] = key; e["url"] = item["url"]; e["attrs"]["tvg-id"] = key
            sync(e, item); by_key[key] = e
            report.append((e["name"], "MIGRATED", f"{old} -> {item['url']}")); continue
        e = entry_from_catalog(item); by_key[key] = e; entries.append(e)
        report.append((e["name"], "NEW", "kamera baru dari sumber"))
    return report


def dedup_urls(entries):
    seen, kept, removed = {}, [], []
    for e in entries:
        if e["url"] in seen: removed.append((e, f"duplikat URL dengan '{seen[e['url']]}'")); continue
        seen[e["url"]] = e["name"]; kept.append(e)
    return kept, removed


def load_history(p):
    if Path(p).exists():
        try: return json.loads(Path(p).read_text(encoding="utf-8"))
        except Exception: pass
    return {}


def update_history(h, kept, results):
    for e in kept:
        ok = results.get(e["key"], (False, ""))[0]
        d = h.setdefault(e["key"], {"total": 0, "ok": 0, "recent": []})
        d["total"] += 1; d["ok"] += 1 if ok else 0
        d["recent"] = (d.get("recent", []) + [bool(ok)])[-HISTORY_LEN:]
        d["uptime_pct"] = round(100.0 * d["ok"] / d["total"]) if d["total"] else 0
    return h


def append_dataset(kept, results, quality):
    Path("data").mkdir(parents=True, exist_ok=True)
    p = Path("data/uptime.csv"); new = not p.exists()
    with p.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new: w.writerow(["date_utc", "key", "name", "group", "online", "resolution", "bandwidth_kbps"])
        d = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        for e in kept:
            q = quality.get(e["key"], {})
            w.writerow([d, e["key"], e["name"], e["attrs"].get("group-title", ""),
                        1 if results.get(e["key"], (False, ""))[0] else 0,
                        q.get("resolution") or "", q.get("bandwidth_kbps") or ""])


def update_changelog(report):
    p = Path("CHANGELOG.md")
    old = p.read_text(encoding="utf-8") if p.exists() else "# Changelog\n"
    body = old.split("\n", 1)[1] if "\n" in old else ""
    icon = {"NEW": "🆕", "REMOVED": "❌", "UPDATED": "🔁", "MIGRATED": "🔁", "ADOPTED": "🔗"}
    lines = [f"## {datetime.now(timezone.utc).strftime('%Y-%m-%d')}"]
    for n, s, note in report:
        if s in icon: lines.append(f"- {icon[s]} **{s}**: {n} — {note}")
    if len(lines) == 1: lines.append("- (tidak ada perubahan kamera)")
    sections = body.split("\n## ")
    body = "\n## ".join(sections[:40])
    p.write_text("# Changelog\n" + "\n".join(lines) + "\n" + body, encoding="utf-8")


def build_status_block(kept, results, history, quality):
    live = sum(1 for e in kept if results.get(e["key"], (False, ""))[0])
    lines = [f"> 🕒 **{wib_now()}** · Total **{len(kept)}** · 🟢 **{live}** · 🔴 **{len(kept)-live}**", "",
             "| Kamera | Grup | Status | Uptime | Kualitas |", "|---|---|:--:|:--:|:--:|"]
    for e in sorted(kept, key=lambda x: (x["attrs"].get("group-title", ""), x["name"].lower())):
        ok = results.get(e["key"], (False, ""))[0]
        up = history.get(e["key"], {}).get("uptime_pct", 100 if ok else 0)
        res = quality.get(e["key"], {}).get("resolution") or "—"
        lines.append(f"| {e['name'].replace('|','\\|')} | {e['attrs'].get('group-title','').replace('|','\\|')} | {'🟢' if ok else '🔴'} | {up}% | {res} |")
    lines += ["", "_🔴 = gagal cek terakhir; dipertahankan maks 3 hari beruntun sebelum dihapus._"]
    return "\n".join(lines)


def update_readme(path, kept, results, history, quality):
    p = Path(path)
    if not p.exists(): return False
    t = p.read_text(encoding="utf-8")
    if README_START not in t or README_END not in t: return False
    block = build_status_block(kept, results, history, quality)
    p.write_text(t.split(README_START, 1)[0] + README_START + "\n" + block + "\n" + README_END + t.split(README_END, 1)[1], encoding="utf-8")
    return True


def generate_thumbs(entries, workers=6):
    Path("thumbs").mkdir(parents=True, exist_ok=True)
    def one(e):
        out = Path("thumbs") / f"{e['key']}.jpg"
        hdr = f"User-Agent: {UA}\r\nReferer: {referer_for(e['url'])}\r\n"
        cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-headers", hdr,
               "-i", e["url"], "-frames:v", "1", "-q:v", "4", "-vf", "scale=320:-2", str(out)]
        try:
            r = subprocess.run(cmd, timeout=25, capture_output=True)
            return r.returncode == 0 and out.exists() and out.stat().st_size > 0
        except Exception:
            return False
    ok = 0
    with cf.ThreadPoolExecutor(max_workers=workers) as ex:
        for r in ex.map(one, entries): ok += 1 if r else 0
    print(f"[✓] Thumbnail: {ok}/{len(entries)} berhasil")


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
    ap.add_argument("--thumbs", action="store_true", help="mode khusus: generate thumbs/*.jpg lalu keluar")
    args = ap.parse_args()

    if args.thumbs:
        generate_thumbs(parse_m3u(args.playlist)); return 0

    state = {}
    if Path(args.state).exists():
        try: state = json.loads(Path(args.state).read_text(encoding="utf-8"))
        except Exception: state = {}
    history = load_history(args.history)
    entries = parse_m3u(args.playlist)
    print(f"[i] Playlist lama: {len(entries)} entri")
    catalog, source_ok = {}, {"palembang": False, "opencctv": False}
    if not args.skip_palembang:
        try:
            it = scrape_palembang(limit=args.limit)
            for x in it: catalog[x["key"]] = x
            source_ok["palembang"] = True; print(f"[+] palembang: {len(it)}")
        except Exception as e: print(f"[!] palembang: {e}")
    if not args.skip_opencctv:
        try:
            it = scrape_opencctv(limit=args.limit, workers=args.workers)
            for x in it: catalog[x["key"]] = x
            source_ok["opencctv"] = True; print(f"[+] opencctv: {len(it)}")
        except Exception as e: print(f"[!] opencctv: {e}")

    report = merge_catalog(entries, catalog)
    entries, dup_removed = dedup_urls(entries)
    for e, why in dup_removed:
        report.append((e["name"], "REMOVED", why)); state.pop(e["key"], None); history.pop(e["key"], None)

    for e in entries:
        src = "palembang" if e["key"].startswith("plb-") else ("opencctv" if e["key"].startswith("oc-") else None)
        if src and source_ok[src] and e["key"] not in catalog:
            st = state.setdefault(e["key"], {"fail": 0, "missing": 0}); st["missing"] = st.get("missing", 0) + 1
        elif src:
            state.setdefault(e["key"], {"fail": 0, "missing": 0})["missing"] = 0

    print(f"[i] Cek {len(entries)} link...")
    results, quality = {}, {}
    with cf.ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(check_stream, e["url"], args.timeout): e for e in entries}
        for fut in cf.as_completed(futs):
            e = futs[fut]; ok, reason, meta = fut.result()
            results[e["key"]] = (ok, reason); quality[e["key"]] = meta
            print(f"    {'OK ' if ok else 'FAIL'} | {e['name']} | {reason}")

    if len(entries) >= 5 and not any(v[0] for v in results.values()):
        print("[!!] SEMUA gagal — kemungkinan geo-block/jaringan. Tidak ada perubahan."); return 0

    kept, removed = [], []
    for e in entries:
        k = e["key"]; st = state.setdefault(k, {"fail": 0, "missing": 0})
        ok, reason = results.get(k, (False, "tidak dicek"))
        st["last_check"] = now_iso(); st["url"] = e["url"]
        if ok:
            st["fail"] = 0; st["last_ok"] = st["last_check"]; kept.append(e); continue
        st["fail"] = st.get("fail", 0) + 1
        is_new = any(n == e["name"] and s == "NEW" for n, s, _ in report)
        if is_new: removed.append((e, "baru tapi mati, dilewati"))
        elif st["fail"] >= args.max_fails: removed.append((e, f"gagal {st['fail']}x beruntun ({reason})"))
        elif st.get("missing", 0) >= args.max_fails: removed.append((e, f"hilang dari sumber {st['missing']} hari"))
        else:
            kept.append(e); report.append((e["name"], "FAIL", f"{reason} (gagal {st['fail']}/{args.max_fails})"))
    for e, why in removed:
        report.append((e["name"], "REMOVED", why)); state.pop(e["key"], None); history.pop(e["key"], None)
        print(f"[-] HAPUS: {e['name']} — {why}")

    history = update_history(history, kept, results)
    live = sum(1 for v in results.values() if v[0])
    summary = {"generated_at": now_iso(), "generated_wib": wib_now(), "total": len(kept),
               "live": live, "offline": len(kept) - live, "removed": len(removed) + len(dup_removed), "sources": source_ok}
    print(f"[i] Ringkasan: {summary}")
    if args.dry_run:
        print("[i] DRY-RUN."); return 0

    write_m3u(args.playlist, kept)
    write_m3u("streams.m3u", kept)
    write_m3u("palembang-kota.m3u8", [e for e in kept if e["key"].startswith("plb-")])
    write_m3u("tol-sumatera.m3u8", [e for e in kept if e["key"].startswith("oc-")])
    Path(args.state).parent.mkdir(parents=True, exist_ok=True)
    Path(args.state).write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
    Path(args.history).write_text(json.dumps(history, indent=2, ensure_ascii=False), encoding="utf-8")
    append_dataset(kept, results, quality)
    update_changelog(report)
    Path("removed.json").write_text(json.dumps([{"key": e["key"], "name": e["name"], "reason": w} for e, w in removed], indent=2, ensure_ascii=False), encoding="utf-8")
    streams = [{"key": e["key"], "name": e["name"], "group": e["attrs"].get("group-title", ""), "url": e["url"],
                "ok": results.get(e["key"], (False, ""))[0], "lat": e.get("lat"), "lng": e.get("lng"),
                "web": e.get("web", web_playable(e["url"])), "uptime_pct": history.get(e["key"], {}).get("uptime_pct", 100),
                "resolution": quality.get(e["key"], {}).get("resolution"),
                "bandwidth_kbps": quality.get(e["key"], {}).get("bandwidth_kbps"),
                "logo": logo_for(e["key"])} for e in kept]
    Path("status.json").write_text(json.dumps({"summary": summary, "streams": streams}, indent=2, ensure_ascii=False), encoding="utf-8")
    md = [f"# Laporan — {summary['generated_at']}", "",
          f"- Total **{summary['total']}** · 🟢 **{summary['live']}** · 🔴 **{summary['offline']}** · dihapus **{summary['removed']}**", "",
          "| Nama | Status | Keterangan |", "|---|---|---|"]
    icon = {"NEW": "🆕", "UPDATED": "🔁", "ADOPTED": "🔗", "MIGRATED": "🔁", "FAIL": "⚠️", "REMOVED": "❌"}
    for n, s, note in report: md.append(f"| {n} | {icon.get(s,'')} {s} | {note} |")
    Path("REPORT.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    if update_readme("README.md", kept, results, history, quality): print("[✓] README diperbarui.")
    print(f"[✓] Selesai. {len(kept)} entri.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
