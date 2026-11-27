#!/usr/bin/env python3
"""Buat pesan siaran WhatsApp siap-copy dari status.json -> wa_broadcast.txt.
Tanpa API pihak ketiga; kamu tinggal tempel isinya ke Channel WA."""
import json, os
from pathlib import Path
from datetime import datetime, timezone, timedelta

REPO = os.environ.get("GITHUB_REPOSITORY", "owner/repo")

def wib():
    return datetime.now(timezone(timedelta(hours=7))).strftime("%d %b %Y %H:%M WIB")

def main():
    p = Path("status.json")
    if not p.exists():
        print("[!] status.json belum ada; jalankan update dulu.")
        return 1
    d = json.loads(p.read_text(encoding="utf-8"))
    s = d.get("summary", {}); streams = d.get("streams", [])
    live = [x for x in streams if x.get("ok")]
    off = [x for x in streams if not x.get("ok")]
    L = ["📹 *PALEMBANG CCTV — LAPORAN HARIAN*", f"🕒 {wib()}",
         f"✅ Live: *{len(live)}* | 🔴 Gangguan: *{len(off)}* | Total: *{s.get('total', len(streams))}*", ""]
    if off:
        L.append("🔴 *Sedang gangguan:*")
        for x in off[:8]: L.append(f"• {x['name']} ({x.get('group','')})")
        if len(off) > 8: L.append(f"• …dan {len(off)-8} lainnya")
        L.append("")
    L.append("🟢 *Live sekarang:*")
    for x in live[:12]: L.append(f"• {x['name']}")
    if len(live) > 12: L.append(f"• …dan {len(live)-12} lainnya")
    L += ["", "🔗 _Playlist HLS:_", f"https://raw.githubusercontent.com/{REPO}/main/streams.m3u8",
          f"⚡ _Mirror CDN:_ https://cdn.jsdelivr.net/gh/{REPO}@main/streams.m3u8",
          "", "_Pantau otomatis • unofficial • open data_"]
    msg = "\n".join(L)
    Path("wa_broadcast.txt").write_text(msg + "\n", encoding="utf-8")
    print(msg)
    print("[✓] wa_broadcast.txt ditulis — tinggal copy ke Channel WA.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
