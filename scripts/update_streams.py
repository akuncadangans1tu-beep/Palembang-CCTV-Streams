#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CCTV Palembang + tol Sumatera + atcsindonesia (hardened). Python 3.9+."""
import argparse, concurrent.futures as cf, csv, gzip, ipaddress, json, os, re, ssl, subprocess, sys, time, zlib
import urllib.error, urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import urljoin, urlsplit, quote

REPO = os.environ.get("GITHUB_REPOSITORY", "owner/repo")
RAW_BASE = f"https://raw.githubusercontent.com/{REPO}/main"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
PALEMBANG_API = "https://cctv.palembang.go.id/api/cctv"
PALEMBANG_STREAM = "https://cctv.palembang.go.id/api/cctv/{id}/playback/index.m3u8"
ATCS_API = "https://atcsindonesia.com/api/cctv"
ATCS_SKIP = {"palembang-cctv"}
OPENCCTV_REGIONS = [("https://opencctv.org/cameras/indonesia/sumatera-selatan", "Tol Palindra", "Palindra "),
                    ("https://opencctv.org/cameras/indonesia/lampung", "Tol Lampung", "Lampung ")]
MAX_FAILS, TIMEOUT, WORKERS, HIST = 3, 12, 10, 30
SSL_CTX = ssl.create_default_context()  # verified default (CWE-295)
ALLOW_INSECURE = ("palembang.go.id",)   # fallback interop cert pemkot (intentional, dismiss alert)
TOKEN_RE = re.compile(r"[?&](token|expires?|expiration|signature|sig|auth|hdnts|hdnea|policy|key-pair-id|exp)=", re.I)
RS, RE_ = "<!-- STATUS:START -->", "<!-- STATUS:END -->"
LS, LE = "<!-- LINKS:START -->", "<!-- LINKS:END -->"
GS, GE = "<!-- GAPS:START -->", "<!-- GAPS:END -->"
HEAD = ["date_utc", "hour_utc", "key", "name", "group", "online", "resolution", "bandwidth_kbps"]
KECAMATAN = ["Bukit Kecil", "Ilir Barat I", "Ilir Barat II", "Ilir Timur I", "Ilir Timur II", "Ilir Timur Tiga",
             "Kemuning", "Kertapati", "Plaju", "Sako", "Seberang Ulu I", "Seberang Ulu II",
             "Sematang Borang", "Sukarami", "Gandus", "Jakabaring", "Kalidoni", "Seberang Ulu Tiga"]
RUAS_TOL = [("Tol Palindra", "Palembang - Indralaya (Sumsel)"), ("Tol Lampung", "Bakauheni - Terbanggi Besar"),
            ("Tol Kayu Agung - Palembang", "Kayu Agung - Palembang"), ("Tol Pematang Panggang - Kayu Agung", "PPKA")]

def now_iso(): return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
def wib_now(): return datetime.now(timezone(timedelta(hours=7))).strftime("%d %b %Y %H:%M WIB")
def norm(s): return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()
def logo(k): return f"{RAW_BASE}/thumbs/{k}.jpg"
def _host(u): return urlsplit(u).netloc.split(":")[0].lower()
def _insecure_ok(h): return any(h == d or h.endswith("." + d) for d in ALLOW_INSECURE)
def _is_private(h):
    try:
        ip = ipaddress.ip_address(h)
        return ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast
    except ValueError:
        return h in ("localhost",) or h.endswith((".localhost", ".internal", ".local"))
def referer(u):
    h = _host(u)
    if h == "palembang.go.id" or h.endswith(".palembang.go.id"): return "https://cctv.palembang.go.id/"
    return "https://opencctv.org/"
def stable(u):
    if not u or not u.lower().startswith(("http://", "https://")): return False
    h = _host(u)
    if not h or _is_private(h): return False
    if h == "opencctv.org" or h.endswith(".opencctv.org"): return False
    if TOKEN_RE.search(u): return False
    return True
def spark(rec): return "".join("▰" if x else "▱" for x in rec[-14:]) or "—"
def flap(rec): return sum(1 for a, b in zip(rec, rec[1:]) if a != b)
def csv_safe(v):
    s = str(v)
    return "'" + s if s and s[0] in "=+-@\t\r" else s

def _read_capped(r, limit):
    buf = bytearray()
    while len(buf) < limit:
        c = r.read(min(65536, limit - len(buf)))
        if not c: break
        buf += c
    return bytes(buf)
def _gunzip_capped(raw, limit):
    d = zlib.decompressobj(16 + zlib.MAX_WBITS)
    out = d.decompress(raw, limit)
    if d.unconsumed_tail or not d.eof: raise ValueError("gzip melebihi batas (bomb?)")
    return out

def http_get(u, timeout=TIMEOUT, max_bytes=300000, retries=2):
    if not stable(u): raise ValueError("URL diblokir (SSRF/invalid)")
    last = None
    for a in range(retries + 1):
        try:
            req = urllib.request.Request(u, headers={"User-Agent": UA, "Referer": referer(u), "Accept": "*/*", "Accept-Encoding": "gzip"})
            with urllib.request.urlopen(req, timeout=timeout, context=SSL_CTX) as r:
                raw = _read_capped(r, max_bytes)
                if r.headers.get("Content-Encoding") == "gzip": raw = _gunzip_capped(raw, max_bytes)
                return r.status, raw
        except urllib.error.HTTPError as e:
            try: b = e.read(2048)
            except Exception: b = b""
            if e.code in (500, 502, 503, 504) and a < retries: last = e; time.sleep(1.5 * (a + 1)); continue
            return e.code, b
        except ssl.SSLError as e:
            if _insecure_ok(_host(u)):
                ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
                try:
                    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
                        raw = _read_capped(r, max_bytes)
                        if r.headers.get("Content-Encoding") == "gzip": raw = _gunzip_capped(raw, max_bytes)
                        return r.status, raw
                except Exception as e2: last = e2
            else: last = e
            if a < retries: time.sleep(1.5 * (a + 1))
        except Exception as e:
            last = e
            if a < retries: time.sleep(1.5 * (a + 1))
    raise last or RuntimeError("gagal " + u)

def uris(t): return [l.strip() for l in t.splitlines() if l.strip() and not l.strip().startswith("#")]

def check(u, timeout=TIMEOUT):
    meta = {}
    if not stable(u): return False, "URL diblokir (SSRF)", meta
    try:
        st, b = http_get(u, timeout)
        if st != 200: return False, f"HTTP {st}", meta
        t = b.decode("utf-8", "ignore")
        if "#EXTM3U" not in t: return False, "bukan M3U8", meta
        base = u
        if "#EXT-X-STREAM-INF" in t:
            res, bw = None, 0
            for l in t.splitlines():
                if l.startswith("#EXT-X-STREAM-INF"):
                    mr, mb = re.search(r"RESOLUTION=(\d+x\d+)", l), re.search(r"BANDWIDTH=(\d+)", l)
                    bb = int(mb.group(1)) if mb else 0
                    if bb >= bw: bw, res = bb, (mr.group(1) if mr else res)
            meta = {"resolution": res, "bandwidth_kbps": round(bw / 1000) if bw else None}
            v = uris(t)
            if not v: return False, "master kosong", meta
            base = urljoin(u, v[0]); st, b = http_get(base, timeout)
            if st != 200: return False, f"varian {st}", meta
            t = b.decode("utf-8", "ignore")
            if "#EXTM3U" not in t: return False, "varian bukan M3U8", meta
        s = uris(t)
        if not s: return False, "tanpa segmen", meta
        st, _ = http_get(urljoin(base, s[0]), timeout, 2048, 1)
        return (st in (200, 206)), ("OK" if st in (200, 206) else f"segmen {st}"), meta
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"[:100], meta

def scrape_palembang(limit=None):
    st, b = http_get(PALEMBANG_API)
    if st != 200: raise RuntimeError(f"palembang {st}")
    data = json.loads(b.decode("utf-8", "ignore")).get("data", [])
    if not data: raise RuntimeError("palembang kosong")
    out = []
    for c in data:
        if c.get("cctv_scope") != "publik" or c.get("cctv_status") != "active" or not c.get("playback_available"): continue
        cid = c.get("cctv_id") or c.get("_id"); name = (c.get("cctv_title") or cid).strip()
        kec = (c.get("kecamatan") or {}).get("namaKecamatan", ""); opd = (c.get("cctv_opd") or {}).get("nama_opd", "")
        g = kec.title() if kec else ("Dishub Palembang" if "Perhubungan" in opd else "Diskominfo Palembang")
        co = (c.get("location") or {}).get("coordinates") or []; lat, lng = (co[1], co[0]) if len(co) >= 2 else (None, None)
        out.append({"key": f"plb-{cid}", "name": name, "group": g, "url": PALEMBANG_STREAM.format(id=c["_id"]), "lat": lat, "lng": lng,
                    "extra": [f"#EXTVLCOPT:http-user-agent={UA}", "#EXTVLCOPT:http-referrer=https://cctv.palembang.go.id/"]})
        if limit and len(out) >= limit: break
    return out

def scrape_atcs(limit=None):
    st, b = http_get(ATCS_API, timeout=60, max_bytes=64000000)
    if st != 200: raise RuntimeError(f"atcs {st}")
    data = json.loads(b.decode("utf-8", "ignore")).get("data", [])
    if not data: raise RuntimeError("atcs kosong")
    out = []
    for c in data:
        if "palembang" not in str(c.get("city", "")).lower(): continue
        if c.get("source") in ATCS_SKIP: continue
        url = c.get("streamingUrl") or c.get("streamingUrlPrimary") or c.get("streamingUrlSecondary") or ""
        if not stable(url): continue
        lat = c.get("latitude", c.get("lat")); lng = c.get("longitude", c.get("lng"))
        out.append({"key": f"atcs-{c.get('id')}", "name": (c.get("title") or c.get("id")).strip(),
                    "group": "Tol Palindra" if "tol" in str(c.get("source", "")) else "Palembang",
                    "url": url, "lat": lat, "lng": lng,
                    "extra": [f"#EXTVLCOPT:http-user-agent={UA}", "#EXTVLCOPT:http-referrer=https://atcsindonesia.com/"]})
        if limit and len(out) >= limit: break
    return out

def _links(ru):
    pages, seen, links = [ru], set(), set()
    while pages and len(seen) < 6:
        p = pages.pop(0)
        if p in seen: continue
        seen.add(p)
        try: st, b = http_get(p)
        except Exception: continue
        if st != 200: continue
        h = b.decode("utf-8", "ignore")
        for href in re.findall(r'href="(/cameras/indonesia/[^"]+)"', h):
            f = "https://opencctv.org" + href
            if re.search(r"-\d+$", href) and href.count("/") >= 5: links.add(f)
            elif href.startswith(ru.replace("https://opencctv.org", "")) and "?page=" in href: pages.append(f)
    return sorted(links)

def html_unescape(s):
    import html as H; return H.unescape(s)

def _m3u8(h):
    c = [html_unescape(s) for t, s in re.findall(r'data-type="([^"]+)"[^>]*?data-src="([^"]+)"', h) if t == "m3u8"]
    c += [html_unescape(s) for s, t in re.findall(r'data-src="([^"]+)"[^>]*?data-type="([^"]+)"', h) if t == "m3u8"]
    c += [html_unescape(m.group(0)) for m in re.finditer(r'https?://[^"\'\s]+\.m3u8[^"\'\s]*', h)]
    return next((u for u in c if stable(u)), None)

def _one(link, g, pre):
    try:
        st, b = http_get(link)
        if st != 200: return None
        h = b.decode("utf-8", "ignore"); u = _m3u8(h)
        if not u: return None
        cid = re.search(r"-(\d+)$", link).group(1)
        m = re.search(r"<h1[^>]*>(.*?)</h1>", h, re.S)
        name = html_unescape(re.sub(r"<[^>]+>", "", m.group(1))).strip() if m else re.sub(r"-\d+$", "", link.rsplit("/", 1)[-1]).replace("-", " ").title()
        if re.match(r"^[\d+\s]+[AB]?$", name): name = pre + name
        ml, mn = re.search(r'data-lat="([-\d.]+)"', h), re.search(r'data-lng="([-\d.]+)"', h)
        lat, lng = (float(ml.group(1)), float(mn.group(1))) if ml and mn else (None, None)
        return {"key": f"oc-{cid}", "name": name, "group": g, "url": u, "lat": lat, "lng": lng, "extra": []}
    except Exception: return None

def scrape_opencctv(limit=None, workers=WORKERS):
    jobs, seen = [], set()
    for ru, g, p in OPENCCTV_REGIONS:
        for l in _links(ru):
            if l not in seen: seen.add(l); jobs.append((l, g, p))
    if not jobs: raise RuntimeError("opencctv kosong")
    if limit: jobs = jobs[:limit]
    out = []
    with cf.ThreadPoolExecutor(max_workers=workers) as ex:
        for f in cf.as_completed([ex.submit(_one, l, g, p) for l, g, p in jobs]):
            r = f.result()
            if r: out.append(r)
    if not out: raise RuntimeError("opencctv tak stabil")
    return out

ATTR = re.compile(r'([\w-]+)="([^"]*)"')
def parse_m3u(p):
    es = []
    if not Path(p).exists(): return es
    cur = None
    for l in Path(p).read_text(encoding="utf-8", errors="ignore").splitlines():
        l = l.strip()
        if not l: continue
        if l.startswith("#EXTINF:"):
            cur = {"attrs": dict(ATTR.findall(l)), "name": l.split(",", 1)[1].strip() if "," in l else "", "extra": [], "url": None}
        elif l.startswith("#"):
            if cur is not None and not l.startswith("#EXTM3U"): cur["extra"].append(l)
        else:
            if cur is None: cur = {"attrs": {}, "name": l, "extra": [], "url": None}
            cur["url"] = l; cur["key"] = cur["attrs"].get("tvg-id") or ("url:" + l); es.append(cur); cur = None
    return es

def from_cat(i):
    return {"attrs": {"tvg-id": i["key"], "tvg-logo": logo(i["key"]), "group-title": i["group"]}, "name": i["name"],
            "extra": list(i.get("extra", [])), "url": i["url"], "key": i["key"], "lat": i.get("lat"), "lng": i.get("lng")}

def write_m3u(p, es):
    L = ["#EXTM3U"]
    for i, e in enumerate(sorted(es, key=lambda x: (x["attrs"].get("group-title", ""), x["name"].lower())), 1):
        e["attrs"]["tvg-chno"] = str(i); e["attrs"]["tvg-country"] = "ID"; e["attrs"]["tvg-language"] = "Indonesian"
        L.append("#EXTINF:-1" + "".join(f' {k}="{v}"' for k, v in e["attrs"].items()) + "," + e["name"])
        L += e.get("extra", []); L.append(e["url"])
    Path(p).write_text("\n".join(L) + "\n", encoding="utf-8")

def merge(es, cat):
    rep = []; bk = {e["key"]: e for e in es}; bu, bn = {}, {}
    for e in es:
        if not e["attrs"].get("tvg-id"): bu.setdefault(e["url"], e); bn.setdefault(norm(e["name"]), e)
    def sync(e, i):
        e["attrs"]["group-title"] = i["group"]; e["attrs"]["tvg-logo"] = logo(i["key"]); e["extra"] = list(i.get("extra", [])); e["lat"], e["lng"] = i.get("lat"), i.get("lng")
    seen = set()
    for k, i in cat.items():
        if i["url"] in seen: continue
        seen.add(i["url"]); e = bk.get(k)
        if e is not None:
            if e["url"] != i["url"]: rep.append((e["name"], "UPDATED", i["url"])); e["url"] = i["url"]
            sync(e, i); continue
        e = bu.pop(i["url"], None)
        if e is not None:
            bn.pop(norm(e["name"]), None); e["key"] = k; e["attrs"]["tvg-id"] = k; sync(e, i); bk[k] = e
            rep.append((e["name"], "ADOPTED", k)); continue
        e = bn.pop(norm(i["name"]), None)
        if e is not None:
            bu.pop(e["url"], None); old = e["url"]; e["key"] = k; e["url"] = i["url"]; e["attrs"]["tvg-id"] = k; sync(e, i); bk[k] = e
            rep.append((e["name"], "MIGRATED", f"{old} -> {i['url']}")); continue
        e = from_cat(i); bk[k] = e; es.append(e); rep.append((e["name"], "NEW", "sumber"))
    return rep

def _namekey(n): return re.sub(r"\bkm\b", "", norm(n)).strip()
def dedup(es):
    seen, seenname, kept, rem = {}, {}, [], []
    for e in es:
        nk = _namekey(e["name"])
        if e["url"] in seen: rem.append((e, f"duplikat URL {seen[e['url']]}")); continue
        if nk and nk in seenname: rem.append((e, f"duplikat nama {seenname[nk]}")); continue
        seen[e["url"]] = e["name"]; seenname[nk] = e["name"]; kept.append(e)
    return kept, rem

def load_hist(p):
    if Path(p).exists():
        try: return json.loads(Path(p).read_text(encoding="utf-8"))
        except Exception: pass
    return {}

def upd_hist(h, kept, res):
    for e in kept:
        ok = res.get(e["key"], (False, ""))[0]; d = h.setdefault(e["key"], {"total": 0, "ok": 0, "recent": []})
        d["total"] += 1; d["ok"] += ok; d["recent"] = (d.get("recent", []) + [bool(ok)])[-HIST:]
        d["uptime_pct"] = round(100 * d["ok"] / d["total"]) if d["total"] else 0
    return h

def normalize_csv(p):
    if not p.exists(): return
    with p.open(encoding="utf-8") as f: rows = list(csv.reader(f))
    if not rows: return
    head, body = rows[0], rows[1:]
    if head == HEAD and all(len(r) == 8 for r in body): return
    out = []
    for r in body:
        if len(r) == 8: out.append(r)
        elif len(r) == 7: out.append([r[0], "00", r[1], r[2], r[3], r[4], r[5], r[6]])
    with p.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(HEAD); w.writerows(out)

def dataset(kept, res, qual):
    Path("data").mkdir(parents=True, exist_ok=True); p = Path("data/uptime.csv")
    normalize_csv(p); new = not p.exists()
    with p.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new: w.writerow(HEAD)
        n = datetime.now(timezone.utc)
        for e in kept:
            q = qual.get(e["key"], {})
            w.writerow([n.strftime("%Y-%m-%d"), n.strftime("%H"), csv_safe(e["key"]), csv_safe(e["name"]),
                        csv_safe(e["attrs"].get("group-title", "")), int(res.get(e["key"], (False, ""))[0]),
                        q.get("resolution") or "", q.get("bandwidth_kbps") or ""])

def hourly():
    p = Path("data/uptime.csv")
    if not p.exists(): return []
    agg = {}
    with p.open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            try: h = (int(r.get("hour_utc", 0)) + 7) % 24; o = int(r.get("online", 0))
            except ValueError: continue
            a = agg.setdefault(h, [0, 0]); a[1] += 1; a[0] += (o == 0)
    return sorted(((h, o, t, round(100 * o / t) if t else 0) for h, (o, t) in agg.items()), key=lambda x: -x[3])[:5]

def uptime_md(kept, res, hist, qual):
    rows = sorted(kept, key=lambda e: -hist.get(e["key"], {}).get("uptime_pct", 0))
    L = [f"# UPTIME & Kualitas — {wib_now()}", "", "## 🏆 Paling stabil", "| Kamera | Uptime | Riwayat |", "|---|---|---|"]
    for e in rows[:10]:
        h = hist.get(e["key"], {}); L.append(f"| {e['name']} | {h.get('uptime_pct',0)}% | {spark(h.get('recent',[]))} |")
    L += ["", "## ⚠️ Paling sering mati", "| Kamera | Uptime | Riwayat |", "|---|---|---|"]
    for e in rows[-10:][::-1]:
        h = hist.get(e["key"], {}); L.append(f"| {e['name']} | {h.get('uptime_pct',0)}% | {spark(h.get('recent',[]))} |")
    fl = [e for e in kept if flap(hist.get(e["key"], {}).get("recent", [])) >= 6]
    L += ["", "## 🔁 Flapping"] + ([f"- {e['name']} ({flap(hist[e['key']]['recent'])} transisi)" for e in fl] or ["- (tidak ada)"])
    rc = {}; tb = 0
    for e in kept:
        q = qual.get(e["key"], {}); rc[q.get("resolution") or "?"] = rc.get(q.get("resolution") or "?", 0) + 1; tb += q.get("bandwidth_kbps") or 0
    L += ["", "## 📺 Kualitas", f"- Total bitrate ≈ **{tb} kbps**", "| Resolusi | Jumlah |", "|---|---|"]
    for r, n in sorted(rc.items(), key=lambda x: -x[1]): L.append(f"| {r} | {n} |")
    hr = hourly()
    L += ["", "## 🕐 Jam rawan offline (WIB)", "| Jam | Offline |", "|---|---|"] + [f"| {h:02d}:00 | {p}% |" for h, o, t, p in hr]
    Path("UPTIME.md").write_text("\n".join(L) + "\n", encoding="utf-8")

def gaps(groups):
    ck = [k for k in KECAMATAN if any(k.lower() in g.lower() for g in groups)]
    ek = [k for k in KECAMATAN if k not in ck]
    ct = [n for n, _ in RUAS_TOL if any(n in g for g in groups)]
    et = [(n, d) for n, d in RUAS_TOL if n not in ct]
    L = [f"# 🗺️ Area Belum Tercakup — {wib_now()}", "", f"_Cakupan **{len(ck)}**/{len(KECAMATAN)} kecamatan & **{len(ct)}**/{len(RUAS_TOL)} ruas tol._", ""]
    if ek:
        L.append(f"## 🏘️ Kecamatan tanpa kamera ({len(ek)})"); L += [f"- [ ] **{k}**" for k in ek]
    else: L.append("## 🎉 Semua kecamatan tercakup!")
    L.append("")
    if et:
        L.append(f"## 🛣️ Ruas tol tanpa kamera ({len(et)})"); L += [f"- [ ] **{n}** — {d}" for n, d in et]
    else: L.append("## 🎉 Semua ruas tol tercakup!")
    L += ["", "## Cara bantu", "1. Issues → Usul kamera baru.", "2. URL .m3u8 + sumber resmi.", "3. Maintainer verifikasi.", "", "_Hanya kamera publik & legal._"]
    Path("GAPS.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    p = Path("README.md")
    if p.exists():
        t = p.read_text(encoding="utf-8")
        if GS in t and GE in t:
            p.write_text(t.split(GS, 1)[0] + GS + f"\n📍 **{len(ek)} kecamatan** & **{len(et)} ruas tol** belum tercakup. [Detail →](GAPS.md)\n" + GE + t.split(GE, 1)[1], encoding="utf-8")

def changelog(rep):
    p = Path("CHANGELOG.md"); old = p.read_text(encoding="utf-8") if p.exists() else "# Changelog\n"
    body = old.split("\n", 1)[1] if "\n" in old else ""
    ic = {"NEW": "🆕", "REMOVED": "❌", "UPDATED": "🔁", "MIGRATED": "🔁", "ADOPTED": "🔗"}
    L = [f"## {datetime.now(timezone.utc).strftime('%Y-%m-%d')}"]
    for n, s, note in rep:
        if s in ic: L.append(f"- {ic[s]} **{s}**: {n} — {note}")
    if len(L) == 1: L.append("- (tidak ada perubahan)")
    p.write_text("# Changelog\n" + "\n".join(L) + "\n" + "\n## ".join(body.split("\n## ")[:40]), encoding="utf-8")

def feed(rep, summary):
    ic = {"NEW": "🆕", "REMOVED": "❌", "UPDATED": "🔁", "MIGRATED": "🔁"}
    e = [f"<entry><title>{ic[s]} {s}: {n}</title><id>urn:{REPO}:{n}:{s}</id><updated>{now_iso()}</updated><summary>{note}</summary></entry>"
         for n, s, note in rep if s in ic]
    Path("feed.xml").write_text(f'<?xml version="1.0" encoding="utf-8"?><feed xmlns="http://www.w3.org/2005/Atom"><title>{REPO} CCTV</title><id>urn:{REPO}</id><updated>{now_iso()}</updated><link href="https://github.com/{REPO}"/>' + "".join(e[:20]) + "</feed>", encoding="utf-8")

def status_block(kept, res, hist, qual):
    live = sum(1 for e in kept if res.get(e["key"], (False, ""))[0])
    L = [f"> 🕒 **{wib_now()}** · **{len(kept)}** kamera · 🟢 {live} · 🔴 {len(kept)-live}", "",
         "| Kamera | Grup | Status | Uptime | Riwayat | Kualitas |", "|---|---|:--:|:--:|---|:--:|"]
    for e in sorted(kept, key=lambda x: (x["attrs"].get("group-title", ""), x["name"].lower())):
        h = hist.get(e["key"], {}); ok = res.get(e["key"], (False, ""))[0]
        L.append(f"| {e['name'].replace('|','\\|')} | {e['attrs'].get('group-title','').replace('|','\\|')} | {'🟢' if ok else '🔴'} | {h.get('uptime_pct',0)}% | {spark(h.get('recent',[]))} | {qual.get(e['key'],{}).get('resolution') or '—'} |")
    return "\n".join(L)

def links_block(repo):
    raw = f"https://raw.githubusercontent.com/{repo}/main/streams.m3u8"
    jsd = f"https://cdn.jsdelivr.net/gh/{repo}@main/streams.m3u8"
    gh = f"https://github.com/{repo}"; sr = quote(f"https://raw.githubusercontent.com/{repo}/main/status.json", safe="")
    return "\n".join([f"[![Update]({gh}/actions/workflows/update-streams.yml/badge.svg)]({gh}/actions/workflows/update-streams.yml)",
        f"[![Kamera](https://img.shields.io/badge/dynamic/json?url={sr}&query=%24.summary.total&label=kamera&color=blue)]({gh}/blob/main/status.json)",
        f"[![Live](https://img.shields.io/badge/dynamic/json?url={sr}&query=%24.summary.live&label=live&color=brightgreen)]({gh}/blob/main/status.json)",
        "", "```text", raw, "```", "", f"Mirror CDN: `{jsd}`", "",
        f"![QR](https://api.qrserver.com/v1/create-qr-code/?size=220x220&data={quote(raw, safe='')})"])

def upd_readme(kept, res, hist, qual):
    p = Path("README.md")
    if not p.exists(): return
    t = p.read_text(encoding="utf-8"); ch = False
    if RS in t and RE_ in t: t = t.split(RS, 1)[0] + RS + "\n" + status_block(kept, res, hist, qual) + "\n" + RE_ + t.split(RE_, 1)[1]; ch = True
    repo = os.environ.get("GITHUB_REPOSITORY")
    if repo and LS in t and LE in t: t = t.split(LS, 1)[0] + LS + "\n" + links_block(repo) + "\n" + LE + t.split(LE, 1)[1]; ch = True
    if ch: p.write_text(t, encoding="utf-8")

def thumbs(es, workers=6):
    Path("thumbs").mkdir(parents=True, exist_ok=True)
    def one(e):
        o = Path("thumbs") / f"{e['key']}.jpg"
        cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-headers", f"User-Agent: {UA}\r\nReferer: {referer(e['url'])}\r\n", "-i", e["url"], "-frames:v", "1", "-q:v", "4", "-vf", "scale=320:-2", str(o)]
        try:
            r = subprocess.run(cmd, timeout=25, capture_output=True); return r.returncode == 0 and o.exists() and o.stat().st_size > 0
        except Exception: return False
    ok = 0
    with cf.ThreadPoolExecutor(max_workers=workers) as ex:
        for r in ex.map(one, es): ok += r
    print(f"[✓] thumbs {ok}/{len(es)}")

def lint(p):
    es = parse_m3u(p); errs = []; seen = set()
    if not Path(p).exists(): errs.append("file tidak ada")
    for e in es:
        if not e.get("url"): errs.append(f"tanpa URL: {e['name']}")
        if e["url"] in seen: errs.append(f"duplikat: {e['url']}")
        seen.add(e["url"])
        if not e["url"].startswith(("http://", "https://")): errs.append(f"URL invalid: {e['url']}")
    for x in errs: print("LINT-ERR:", x)
    print(f"[lint] {len(es)} entri, {len(errs)} error")
    return 1 if errs else 0

def rotate(days=60):
    p = Path("data/uptime.csv")
    if not p.exists(): return
    normalize_csv(p)
    cut = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    keep, arch = [], {}
    with p.open(encoding="utf-8") as f:
        rd = csv.reader(f); head = next(rd)
        for r in rd: (keep if r[0] >= cut else arch.setdefault(r[0][:7], [])).append(r)
    Path("data/archive").mkdir(parents=True, exist_ok=True)
    for mo, rows in arch.items():
        ap = Path(f"data/archive/uptime-{mo}.csv"); new = not ap.exists()
        with ap.open("a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if new: w.writerow(head)
            w.writerows(rows)
    with p.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(head); w.writerows(keep)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--playlist", default="streams.m3u8"); ap.add_argument("--state", default="scripts/state.json")
    ap.add_argument("--history", default="history.json"); ap.add_argument("--max-fails", type=int, default=MAX_FAILS)
    ap.add_argument("--workers", type=int, default=WORKERS); ap.add_argument("--timeout", type=int, default=TIMEOUT)
    ap.add_argument("--limit", type=int); ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--thumbs", action="store_true"); ap.add_argument("--lint", action="store_true"); ap.add_argument("--rotate", action="store_true")
    a = ap.parse_args()
    if a.lint: return lint(a.playlist)
    if a.rotate: rotate(); return 0
    if a.thumbs: thumbs(parse_m3u(a.playlist)); return 0
    state = {}
    if Path(a.state).exists():
        try: state = json.loads(Path(a.state).read_text(encoding="utf-8"))
        except Exception: state = {}
    hist = load_hist(a.history); es = parse_m3u(a.playlist)
    print(f"[i] lama {len(es)}")
    cat, sok = {}, {"palembang": False, "opencctv": False, "atcs": False}
    for name, fn in (("palembang", scrape_palembang), ("atcs", scrape_atcs), ("opencctv", scrape_opencctv)):
        try:
            it = fn(a.limit) if name != "opencctv" else fn(a.limit, a.workers)
            for x in it: cat[x["key"]] = x
            sok[name] = True; print(f"[+] {name} {len(it)}")
        except Exception as e: print(f"[!] {name}", e)
    rep = merge(es, cat); es, dup = dedup(es)
    for e, w in dup: rep.append((e["name"], "REMOVED", w)); state.pop(e["key"], None); hist.pop(e["key"], None)
    for e in es:
        src = ("palembang" if e["key"].startswith("plb-") else "atcs" if e["key"].startswith("atcs-") else "opencctv" if e["key"].startswith("oc-") else None)
        if src and sok[src] and e["key"] not in cat:
            s = state.setdefault(e["key"], {"fail": 0, "missing": 0}); s["missing"] = s.get("missing", 0) + 1
        elif src: state.setdefault(e["key"], {"fail": 0, "missing": 0})["missing"] = 0
    res, qual = {}, {}
    with cf.ThreadPoolExecutor(max_workers=a.workers) as ex:
        fu = {ex.submit(check, e["url"], a.timeout): e for e in es}
        for f in cf.as_completed(fu):
            e = fu[f]; ok, r, m = f.result(); res[e["key"]] = (ok, r); qual[e["key"]] = m
            print(f"    {'OK ' if ok else 'FAIL'} | {e['name']} | {r}")
    if len(es) >= 5 and not any(v[0] for v in res.values()):
        print("[!!] semua gagal; tidak ada perubahan"); return 0
    kept, rem = [], []
    for e in es:
        k = e["key"]; s = state.setdefault(k, {"fail": 0, "missing": 0}); ok, r = res.get(k, (False, "?"))
        s["last_check"] = now_iso(); s["url"] = e["url"]
        if ok: s["fail"] = 0; s["last_ok"] = s["last_check"]; kept.append(e); continue
        s["fail"] = s.get("fail", 0) + 1
        new = any(n == e["name"] and st == "NEW" for n, st, _ in rep)
        if new: rem.append((e, "baru tapi mati"))
        elif s["fail"] >= a.max_fails: rem.append((e, f"gagal {s['fail']}x ({r})"))
        elif s.get("missing", 0) >= a.max_fails: rem.append((e, f"hilang {s['missing']} hari"))
        else: kept.append(e); rep.append((e["name"], "FAIL", f"{r} ({s['fail']}/{a.max_fails})"))
    for e, w in rem: rep.append((e["name"], "REMOVED", w)); state.pop(e["key"], None); hist.pop(e["key"], None); print("[-]", e["name"], w)
    hist = upd_hist(hist, kept, res); live = sum(1 for v in res.values() if v[0])
    summ = {"generated_at": now_iso(), "generated_wib": wib_now(), "total": len(kept), "live": live, "offline": len(kept) - live, "removed": len(rem) + len(dup), "sources": sok}
    print("[i]", summ)
    if a.dry_run: print("[i] dry-run"); return 0
    write_m3u(a.playlist, kept)
    Path(a.state).parent.mkdir(parents=True, exist_ok=True)
    Path(a.state).write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
    Path(a.history).write_text(json.dumps(hist, indent=2, ensure_ascii=False), encoding="utf-8")
    dataset(kept, res, qual); changelog(rep); feed(rep, summ); uptime_md(kept, res, hist, qual)
    gaps({e["attrs"].get("group-title", "") for e in kept})
    Path("removed.json").write_text(json.dumps([{"key": e["key"], "name": e["name"], "reason": w} for e, w in rem], ensure_ascii=False), encoding="utf-8")
    streams = [{"key": e["key"], "name": e["name"], "group": e["attrs"].get("group-title", ""), "url": e["url"], "ok": res.get(e["key"], (False, ""))[0],
                "lat": e.get("lat"), "lng": e.get("lng"), "uptime_pct": hist.get(e["key"], {}).get("uptime_pct", 100),
                "resolution": qual.get(e["key"], {}).get("resolution"), "bandwidth_kbps": qual.get(e["key"], {}).get("bandwidth_kbps"), "logo": logo(e["key"])} for e in kept]
    Path("status.json").write_text(json.dumps({"summary": summ, "streams": streams}, indent=2, ensure_ascii=False), encoding="utf-8")
    Path("playlist.json").write_text(json.dumps({"channels": [{"name": s["name"], "group": s["group"], "url": s["url"], "tvg-id": s["key"], "tvg-logo": s["logo"]} for s in streams]}, indent=2, ensure_ascii=False), encoding="utf-8")
    md = [f"# Laporan — {summ['generated_at']}", "", f"- **{summ['total']}** · 🟢{summ['live']} · 🔴{summ['offline']} · hapus {summ['removed']}", "", "| Nama | Status | Ket |", "|---|---|---|"]
    ic = {"NEW": "🆕", "UPDATED": "🔁", "ADOPTED": "🔗", "MIGRATED": "🔁", "FAIL": "⚠️", "REMOVED": "❌"}
    for n, s, note in rep: md.append(f"| {n} | {ic.get(s,'')} {s} | {note} |")
    Path("REPORT.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    upd_readme(kept, res, hist, qual); print(f"[✓] {len(kept)} entri")
    return 0

if __name__ == "__main__":
    sys.exit(main())
