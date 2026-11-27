#!/usr/bin/env python3
"""Analisis celah coverage: kecamatan Palembang & ruas tol JTTS yang BELUM punya kamera -> COVERAGE.md."""
import json
from pathlib import Path

KEC = ["Ilir Barat I", "Ilir Barat II", "Ilir Timur I", "Ilir Timur II", "Ilir Timur III",
       "Jakabaring", "Kalidoni", "Kemuning", "Kertapati", "Plaju", "Sako", "Seberang Ulu I",
       "Seberang Ulu II", "Sematang Borang", "Sukarami", "Gandus", "Bukit Kecil", "Alang-Alang Lebar"]
TOL = [("Palembang–Indralaya (Palindra)", "palindra"),
       ("Indralaya–Prabumulih", "prabumulih"),
       ("Kayu Agung–Palembang (Kapal)", "kapal"),
       ("Palembang–Betung", "betung"),
       ("Betung–Jambi", "jambi"),
       ("Bakauheni–Terbanggi Besar", "bakauheni"),
       ("Terbanggi Besar–Pematang Panggang–Kayu Agung", "pematang"),
       ("Pekanbaru–Dumai", "dumai"),
       ("Ruas Lampung lainnya", "lampung")]

def norm(s): return "".join(ch.lower() for ch in s if ch.isalnum())

def main():
    p = Path("status.json")
    if not p.exists():
        print("[!] status.json belum ada; jalankan update dulu."); return 1
    streams = json.loads(p.read_text(encoding="utf-8")).get("streams", [])
    groups = {norm(s.get("group", "")) for s in streams}
    blob = norm(" ".join((s.get("group", "") + " " + s.get("name", "")) for s in streams))
    gap_kec = [k for k in KEC if norm(k) not in groups]
    gap_tol = [(n, kw) for n, kw in TOL if kw not in blob]
    L = ["# Coverage & Area yang Belum Terjangkau", "",
         f"> Dibuat otomatis dari `status.json` ({len(streams)} kamera). Jangan edit manual.", "",
         "## 🏙️ Kecamatan Palembang", "| Kecamatan | Status |", "|---|---|"]
    for k in KEC:
        L.append(f"| {k} | {'❌ belum ada' if k in gap_kec else '✅ ada kamera'} |")
    L += ["", f"**{len(gap_kec)} kecamatan belum terjangkau.**",
          "Kalau kamu tahu kamera **publik** di area ini, buka issue *Usul kamera baru* — kontribusi paling berharga!", "",
          "## 🛣️ Ruas Tol Sumatera (JTTS)", "| Ruas | Status |", "|---|---|"]
    for n, kw in TOL:
        L.append(f"| {n} | {'❌ belum' if kw in [k for _, k in gap_tol] else '✅ tercover'} |")
    L += ["", f"**{len(gap_tol)} ruas belum tercover.**", "",
          "_Cakupan saat ini fokus Palembang + koridor tol yang sumbernya stabil & publik._"]
    Path("COVERAGE.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"[✓] COVERAGE.md: {len(gap_kec)} kecamatan & {len(gap_tol)} ruas belum tercover")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
