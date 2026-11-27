#!/usr/bin/env python3
"""Daftar area yang belum tercakup kamera, ditulis ke GAPS.md + README (blok GAPS).
Dibandingkan dengan grup yang ada di status.json."""
import json, re
from pathlib import Path
from datetime import datetime, timezone, timedelta

REPO = "akuncadangans1tu-beep/Palembang-CCTV-Streams"

# Daftar resmi wilayah yang HARUSNYA tercakup
KECAMATAN_PALEMBANG = [
    "Bukit Kecil", "Ilir Barat I", "Ilir Barat II", "Ilir Timur I", "Ilir Timur II", "Ilir Timur Tiga",
    "Kemuning", "Kertapati", "Plaju", "Sako", "Seberang Ulu I", "Seberang Ulu II",
    "Sematang Borang", "Sukarami", "Gandus", "Jakabaring", "Kalidoni", "Seberang Ulu Tiga",
]
RUAS_TOL = [
    ("Tol Palindra", "Palembang - Indralaya (Sumsel)"),
    ("Tol Lampung", "Bakauheni - Terbanggi Besar & sekitarnya"),
    ("Tol Kayu Agung - Palembang", "Kayu Agung - Palembang (Baki)"),
    ("Tol Pematang Panggang - Kayu Agung", "PPKA"),
]
GAPS_START = "<!-- GAPS:START -->"; GAPS_END = "<!-- GAPS:END -->"


def wib():
    return datetime.now(timezone(timedelta(hours=7))).strftime("%d %b %Y %H:%M WIB")


def get_groups():
    p = Path("status.json")
    if not p.exists():
        return set()
    data = json.loads(p.read_text(encoding="utf-8"))
    return {s.get("group", "") for s in data.get("streams", []) if s.get("group")}


def kecamatan_covered(groups, kec):
    # Match longgar: "Ilir Timur" match dengan "Ilir Timur I", dll.
    n = kec.lower()
    for g in groups:
        if n in g.lower():
            return True
    return False


def main():
    groups = get_groups()
    covered_kec = [k for k in KECAMATAN_PALEMBANG if kecamatan_covered(groups, k)]
    empty_kec = [k for k in KECAMATAN_PALEMBANG if not kecamatan_covered(groups, k)]
    covered_tol = [n for n, _ in RUAS_TOL if any(n in g for g in groups)]
    empty_tol = [(n, d) for n, d in RUAS_TOL if not any(n in g for g in groups)]

    # Tulis GAPS.md
    L = [f"# 🗺️ Area Belum Tercakup — {wib()}", "",
         f"_Playlist saat ini mencakup **{len(covered_kec)}** dari {len(KECAMATAN_PALEMBANG)} kecamatan di Palembang, dan **{len(covered_tol)}** ruas tol._", ""]
    if empty_kec:
        L.append(f"## 🏘️ Kecamatan Palembang tanpa kamera ({len(empty_kec)})")
        for k in empty_kec:
            L.append(f"- [ ] **{k}**")
        L += ["", "_Kalau kamu tahu CCTV publik resmi (Diskominfo / Dishub / portal pemkot) di kecamatan ini, buka issue `Usul kamera baru`._"]
    else:
        L.append("## 🎉 Semua kecamatan Palembang sudah tercakup!")
    L.append("")
    if empty_tol:
        L.append(f"## 🛣️ Ruas tol tanpa kamera ({len(empty_tol)})")
        for n, d in empty_tol:
            L.append(f"- [ ] **{n}** — {d}")
        L += ["", "_Kalau kamu tahu portal CCTV publik ruas tol ini (Hutama Karya / Jasamarga / Pemprov), buka issue `Usul kamera baru`._"]
    else:
        L.append("## 🎉 Semua target ruas tol sudah tercakup!")
    L += ["", "## Cara bantu mengisi kekosongan", "",
          "1. Buka **Issues → New issue → Usul kamera baru**.",
          "2. Sertakan URL `.m3u8` dan sumber resminya.",
          "3. Maintainer verifikasi & tambahkan ke playlist.",
          "", "_Hanya kamera publik & legal. Kamera pribadi (rumah/kantor) tidak diterima._"]
    Path("GAPS.md").write_text("\n".join(L) + "\n", encoding="utf-8")

    # Update README (blok GAPS)
    p = Path("README.md")
    if p.exists():
        t = p.read_text(encoding="utf-8")
        if GAPS_START in t and GAPS_END in t:
            summary = (f"📍 **{len(empty_kec)} kecamatan** Palembang & **{len(empty_tol)} ruas tol** belum tercakup. "
                       f"[Lihat detail & cara bantu →](GAPS.md)")
            new = t.split(GAPS_START, 1)[0] + GAPS_START + "\n" + summary + "\n" + GAPS_END + t.split(GAPS_END, 1)[1]
            p.write_text(new, encoding="utf-8")
    print(f"[✓] GAPS: {len(empty_kec)} kecamatan + {len(empty_tol)} ruas tol kosong")


if __name__ == "__main__":
    main()
