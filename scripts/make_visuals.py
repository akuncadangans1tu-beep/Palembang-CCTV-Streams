#!/usr/bin/env python3
"""Visual statis: --map --chart --mosaic --banner --postcard --heatmap; tanpa flag = semua kecuali postcard.
Selalu menulis file (placeholder bila sumber belum ada). matplotlib lazy; yang lain cukup Pillow."""
import argparse, json, csv, random
from pathlib import Path
from datetime import datetime, timezone, timedelta, date as ddate
from PIL import Image, ImageDraw, ImageFont

A = Path("assets"); A.mkdir(exist_ok=True)
S = json.loads(Path("status.json").read_text(encoding="utf-8")) if Path("status.json").exists() else {"summary": {}, "streams": []}

def font(sz):
    try: return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", sz)
    except Exception: return ImageFont.load_default()

def placeholder(fn, text):
    im = Image.new("RGB", (640, 360), "#0b0f14"); d = ImageDraw.Draw(im)
    d.text((20, 150), text, fill="#8b98a5", font=font(20))
    d.text((20, 185), "akan terisi otomatis setelah data tersedia", fill="#556", font=font(14))
    im.save(A / fn)

def _plt():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    return plt

def _daily():
    p = Path("data/uptime.csv"); day = {}
    if not p.exists(): return day
    with p.open(encoding="utf-8") as f:
        rd = csv.reader(f); next(rd, None)
        for r in rd:
            if len(r) == 8: d, o = r[0], r[5]
            elif len(r) == 7: d, o = r[0], r[4]
            else: continue
            try: o = int(o)
            except ValueError: continue
            if o not in (0, 1): continue
            a = day.setdefault(d, [0, 0]); a[1] += 1; a[0] += o
    return day

def pmap():
    plt = _plt()
    pts = [(s["lng"], s["lat"], s["ok"]) for s in S["streams"] if s.get("lat") and s.get("lng")]
    if not pts: placeholder("map.png", "Peta menunggu data koordinat"); return
    fig, ax = plt.subplots(figsize=(8, 8), dpi=110); fig.patch.set_facecolor("#0b0f14"); ax.set_facecolor("#0b0f14")
    for x, y, ok in pts: ax.scatter(x, y, c="#22c55e" if ok else "#ef4444", s=40, edgecolors="white", linewidths=.5)
    ax.set_title("Coverage CCTV Palembang", color="white"); ax.tick_params(colors="white"); ax.grid(alpha=.2)
    for sp in ax.spines.values(): sp.set_color("#333")
    fig.savefig(A / "map.png", bbox_inches="tight"); plt.close(fig)

def chart():
    plt = _plt(); day = _daily(); ks = sorted(day)[-30:]
    if not ks: placeholder("uptime.png", "Grafik menunggu data uptime"); return
    fig, ax = plt.subplots(figsize=(9, 3.5), dpi=110); fig.patch.set_facecolor("#0b0f14"); ax.set_facecolor("#0b0f14")
    ax.plot(ks, [day[k][0] for k in ks], color="#22c55e", marker="o"); ax.tick_params(colors="white", axis="x", rotation=90, labelsize=6)
    ax.set_title("Kamera live per hari", color="white"); ax.grid(alpha=.2)
    for sp in ax.spines.values(): sp.set_color("#333")
    fig.savefig(A / "uptime.png", bbox_inches="tight"); plt.close(fig)

def heatmap():
    plt = _plt(); import numpy as np
    day = _daily()
    if not day: placeholder("heatmap.png", "Heatmap menunggu data"); return
    cells = {}
    for dstr, (live, tot) in day.items():
        try: d = ddate.fromisoformat(dstr)
        except ValueError: continue
        cells[d] = (live / tot) if tot else 0
    if not cells: placeholder("heatmap.png", "Heatmap menunggu data"); return
    start = min(cells) - timedelta(days=min(cells).weekday())
    nw = (max(cells) - start).days // 7 + 1
    MAT = np.full((7, nw), np.nan)
    for d, r in cells.items():
        MAT[d.weekday(), (d - start).days // 7] = r
    fig, ax = plt.subplots(figsize=(nw * 0.32 + 2, 3.2), dpi=110); fig.patch.set_facecolor("#0b0f14")
    im = ax.imshow(MAT, cmap="RdYlGn", aspect="auto", vmin=0, vmax=1)
    ax.set_yticks(range(7)); ax.set_yticklabels(["Sen", "Sel", "Rab", "Kam", "Jum", "Sab", "Min"], color="white", fontsize=7)
    ax.set_xticks([]); ax.set_title("Kalender uptime harian (hijau = sehat)", color="white", fontsize=10)
    fig.colorbar(im, ax=ax, fraction=0.02)
    fig.savefig(A / "heatmap.png", bbox_inches="tight"); plt.close(fig)

def mosaic():
    th = sorted(Path("thumbs").glob("*.jpg"))[:64]
    if not th: placeholder("mosaic.jpg", "Mosaic menunggu thumbnail"); return
    cols = 8; tw, thh = 160, 90; rows = (len(th) + cols - 1) // cols
    canvas = Image.new("RGB", (cols * tw, rows * thh), "#0b0f14")
    for i, t in enumerate(th):
        try:
            im = Image.open(t).convert("RGB").resize((tw, thh)); canvas.paste(im, ((i % cols) * tw, (i // cols) * thh))
        except Exception: pass
    canvas.save(A / "mosaic.jpg", quality=85)

def banner():
    s = S.get("summary", {}); im = Image.new("RGB", (1280, 640), "#0b0f14"); d = ImageDraw.Draw(im)
    d.text((60, 200), "Palembang CCTV Streams", fill="white", font=font(64))
    d.text((60, 300), f"{s.get('live',0)}/{s.get('total',0)} kamera live - auto-update harian", fill="#22c55e", font=font(32))
    d.text((60, 360), "HLS stabil - open data - unofficial", fill="#8b98a5", font=font(24))
    im.save(A / "banner.png")

def postcard():
    th = sorted(Path("thumbs").glob("*.jpg"))
    if not th: placeholder("postcard.jpg", "Postcard menunggu thumbnail"); return
    t = random.choice(th); im = Image.open(t).convert("RGB").resize((640, 360)); d = ImageDraw.Draw(im)
    wib = datetime.now(timezone(timedelta(hours=7))).strftime("%d %b %Y %H:%M WIB")
    d.rectangle([0, 320, 640, 360], fill="#000000cc"); d.text((12, 330), f"Postcard {wib}", fill="white", font=font(20))
    im.save(A / "postcard.jpg", quality=88)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    for f in ("map", "chart", "mosaic", "banner", "postcard", "heatmap"): ap.add_argument(f"--{f}", action="store_true")
    a = ap.parse_args()
    if a.postcard: postcard()
    elif a.map: pmap()
    elif a.chart: chart()
    elif a.mosaic: mosaic()
    elif a.banner: banner()
    elif a.heatmap: heatmap()
    else: pmap(); chart(); heatmap(); mosaic(); banner()
    print("[✓] visuals selesai")
