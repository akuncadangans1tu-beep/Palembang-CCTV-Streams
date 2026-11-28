#!/usr/bin/env python3
"""Enrich: #1 checksum+version, #5 perubahan resolusi, #6 health score, #7 week-over-week."""
import json, hashlib, csv
from pathlib import Path
from datetime import datetime, timezone, timedelta

def load(p, d):
    try: return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception: return d

def flap(rec): return sum(1 for a, b in zip(rec, rec[1:]) if a != b)

def main():
    now = datetime.now(timezone.utc)
    # #1 checksum + version tag
    pf = Path("streams.m3u8")
    if pf.exists():
        h = hashlib.sha256(pf.read_bytes()).hexdigest()
        Path("streams.m3u8.sha256").write_text(f"{h}  streams.m3u8\n", encoding="utf-8")
        meta = load("playlist.meta.json", {"version": "0.0.0", "sha256": ""})
        if meta.get("sha256") != h:
            a, b, c = (meta.get("version", "0.0.0").split(".") + ["0", "0"])[:3]
            meta["version"] = f"{a}.{b}.{int(c)+1}"
        meta["sha256"] = h; meta["updated"] = now.strftime("%Y-%m-%dT%H:%M:%SZ")
        Path("playlist.meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
        Path("VERSION").write_text(meta["version"] + "\n", encoding="utf-8")
    # #5 deteksi perubahan resolusi -> changelog
    status = load("status.json", {"summary": {}, "streams": []})
    hist = load("history.json", {})
    prev = load("resolutions.json", {})
    cur_map, changes = {}, []
    for s in status["streams"]:
        k = s["key"]; cur = s.get("resolution")
        if cur: cur_map[k] = cur
        old = prev.get(k)
        if old and cur and old != cur: changes.append((s["name"], old, cur))
    Path("resolutions.json").write_text(json.dumps(cur_map, indent=2), encoding="utf-8")
    if changes:
        p = Path("CHANGELOG.md"); old = p.read_text(encoding="utf-8") if p.exists() else "# Changelog\n"
        body = old.split("\n", 1)[1] if "\n" in old else ""
        L = [f"## {now.strftime('%Y-%m-%d')} (resolusi)"] + [f"- 📺 **RESOLUTION**: {n} — {o} -> {c}" for n, o, c in changes]
        p.write_text("# Changelog\n" + "\n".join(L) + "\n" + body, encoding="utf-8")
    # #6 health score komposit
    for s in status["streams"]:
        h = hist.get(s["key"], {})
        up = s.get("uptime_pct", 100); fl = flap(h.get("recent", []))
        res = s.get("resolution") or ""
        bonus = 10 if "1920" in res else 5 if "1280" in res else 0
        s["health"] = max(0, min(100, round(up - 5 * fl + bonus)))
    Path("status.json").write_text(json.dumps(status, indent=2, ensure_ascii=False), encoding="utf-8")
    rows = sorted(status["streams"], key=lambda s: -s.get("health", 0))
    L = [f"# 🩺 Health Score — {now.strftime('%d %b %Y %H:%M UTC')}", "",
         "_score = uptime − 5×flapping + bonus resolusi (1080p +10, 720p +5), clamp 0–100._", "",
         "| # | Kamera | Health | Uptime | Resolusi |", "|---|---|---|---|---|"]
    for i, s in enumerate(rows, 1):
        L.append(f"| {i} | {s['name']} | {s.get('health',0)} | {s.get('uptime_pct',0)}% | {s.get('resolution') or '—'} |")
    Path("HEALTH.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    # #7 week-over-week
    per = {}
    p = Path("data/uptime.csv")
    if p.exists():
        cut1 = (now - timedelta(days=7)).strftime("%Y-%m-%d")
        cut2 = (now - timedelta(days=14)).strftime("%Y-%m-%d")
        with p.open(encoding="utf-8") as f:
            for r in csv.DictReader(f):
                d = r.get("date_utc", ""); k = r.get("key", "")
                try: o = int(r.get("online", 0))
                except ValueError: continue
                bucket = "cur" if d >= cut1 else ("prev" if d >= cut2 else None)
                if not bucket: continue
                a = per.setdefault(k, {"name": r.get("name", k), "cur": [0, 0], "prev": [0, 0]})
                a[bucket][1] += 1; a[bucket][0] += o
    wow = []
    for k, a in per.items():
        c = a["cur"][0] / a["cur"][1] * 100 if a["cur"][1] else None
        pv = a["prev"][0] / a["prev"][1] * 100 if a["prev"][1] else None
        if c is not None and pv is not None: wow.append((a["name"], pv, c, c - pv))
    up = sorted([w for w in wow if w[3] > 0], key=lambda x: -x[3])[:10]
    dn = sorted([w for w in wow if w[3] < 0], key=lambda x: x[3])[:10]
    L = [f"# 📈 Week-over-Week — {now.strftime('%d %b %Y')}", "",
         "## Membaik (7 hari terakhir vs 7 hari sebelumnya)", "| Kamera | Sebelumnya | Sekarang | Δ |", "|---|---|---|---|"]
    L += [f"| {n} | {pv:.0f}% | {c:.0f}% | +{d:.0f} |" for n, pv, c, d in up] or ["| (tidak ada) | | | |"]
    L += ["", "## Menurun", "| Kamera | Sebelumnya | Sekarang | Δ |", "|---|---|---|---|"]
    L += [f"| {n} | {pv:.0f}% | {c:.0f}% | {d:.0f} |" for n, pv, c, d in dn] or ["| (tidak ada) | | | |"]
    Path("WOW.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("[✓] enrich: checksum+version, resolusi, health, wow")

if __name__ == "__main__":
    main()
