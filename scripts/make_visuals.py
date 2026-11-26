#!/usr/bin/env python3
"""Visual statis: --map --chart --mosaic --banner --postcard; tanpa flag = map+chart+mosaic+banner.
matplotlib di-import lazy (hanya map/chart), jadi --postcard/--mosaic/--banner cukup Pillow."""
import argparse, json, csv, random
from pathlib import Path
from datetime import datetime, timezone, timedelta
from PIL import Image, ImageDraw, ImageFont

A = Path("assets"); A.mkdir(exist_ok=True)
S = json.loads(Path("status.json").read_text(encoding="utf-8")) if Path("status.json").exists() else {"summary": {}, "streams": []}

def font(sz):
    try: return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", sz)
    except Exception: return ImageFont.load_default()

def _plt():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    return plt

def pmap():
    plt = _plt()
    pts = [(s["lng"], s["lat"], s["ok"]) for s in S["streams"] if s.get("lat") and s.get("lng")]
    if not pts: return
    fig, ax = plt.subplots(figsize=(8, 8), dpi=110); fig.patch.set_facecolor("#0b0f14"); ax.set_facecolor("#0b0f14")
    for x, y, ok in pts: ax.scatter(x, y, c="#22c55e" if ok else "#ef4444", s=40, edgecolors="white", linewidths=.5)
    ax.set_title("Coverage CCTV Palembang", color="white"); ax.tick_params(colors="white"); ax.grid(alpha=.2)
    for sp in ax.spines.values(): sp.set_color("#333")
    fig.savefig(A / "map.png", bbox_inches="tight"); plt.close(fig)

def chart():
    plt = _plt()
    p = Path("data/uptime.csv")
    if not p.exists(): return
    day = {}
    with p.open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            d = day.setdefault(r["date_utc"], [0, 0]); d[1] += 1; d[0] += int(r["online"])
    ks = sorted(day)[-30:]
    if not ks: return
    fig, ax = plt.subplots(figsize=(9, 3.5), dpi=110); fig.patch.set_facecolor("#0b0f14"); ax.set_facecolor("#0b0f14")
    ax.plot(ks, [day[k][0] for k in ks], color="#22c55e", marker="o"); ax.tick_params(colors="white", axis="x", rotation=90, labelsize=6)
    ax.set_title("Kamera live per hari", color="white"); ax.grid(alpha=.2)
    for sp in ax.spines.values(): sp.set_color("#333")
    fig.savefig(A / "uptime.png", bbox_inches="tight"); plt.close(fig)

def mosaic():
    th = sorted(Path("thumbs").glob("*.jpg"))[:64]
    if not th: return
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
    if not th: return
    t = random.choice(th); im = Image.open(t).convert("RGB").resize((640, 360)); d = ImageDraw.Draw(im)
    wib = datetime.now(timezone(timedelta(hours=7))).strftime("%d %b %Y %H:%M WIB")
    d.rectangle([0, 320, 640, 360], fill="#000000cc"); d.text((12, 330), f"Postcard {wib}", fill="white", font=font(20))
    im.save(A / "postcard.jpg", quality=88)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    for f in ("map", "chart", "mosaic", "banner", "postcard"): ap.add_argument(f"--{f}", action="store_true")
    a = ap.parse_args()
    if a.postcard: postcard()
    elif a.map: pmap()
    elif a.chart: chart()
    elif a.mosaic: mosaic()
    elif a.banner: banner()
    else: pmap(); chart(); mosaic(); banner()
    print("[✓] visuals selesai")
