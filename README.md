# 📹 Palembang CCTV Streams (Unofficial)

[![Update](https://github.com/akuncadangans1tu-beep/Palembang-CCTV-Streams/actions/workflows/update-streams.yml/badge.svg)](https://github.com/akuncadangans1tu-beep/Palembang-CCTV-Streams/actions/workflows/update-streams.yml)
[![Kamera](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fraw.githubusercontent.com%2Fakuncadangans1tu-beep%2FPalembang-CCTV-Streams%2Fmain%2Fstatus.json&query=%24.summary.total&label=kamera&color=blue)](https://github.com/akuncadangans1tu-beep/Palembang-CCTV-Streams/blob/main/status.json)
[![Live](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fraw.githubusercontent.com%2Fakuncadangans1tu-beep%2FPalembang-CCTV-Streams%2Fmain%2Fstatus.json&query=%24.summary.live&label=live&color=brightgreen)](https://github.com/akuncadangans1tu-beep/Palembang-CCTV-Streams/blob/main/status.json)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

Playlist CCTV publik Kota Palembang & koridor tol Sumatera, HLS stabil, **dirawat otomatis tiap hari**. Ala IPTV-Org, tapi fokus Palembang.

## 🚧 Status Proyek
Dirawat otomatis tiap hari. Sebagian kamera bisa offline sesaat (wajar, biasanya pulih sendiri); cakupan terus bertambah.

## ⚠️ Disclaimer Penting (Sanggahan)
Pengembangan independen, **tidak berhubungan resmi** dengan instansi pemerintah mana pun.
* **Bukan Produk DisHub** — tidak bekerja sama / didukung / memakai server internal DisHub.
* **Tidak Terafiliasi dengan Gubernur** Sumsel maupun Pemkot Palembang.
* **Sumber Data** — seluruh tautan dari sumber publik yang terbuka di internet.

## 📡 Sumber
| Sumber | Cakupan |
|---|---|
| `cctv.palembang.go.id` (API publik) | Kamera kota Palembang (per kecamatan) |
| `opencctv.org` → `pub.hk-opt.com` (Hutama Karya) | Tol Palindra & Tol Lampung (JTTS) |

Hanya HLS langsung yang **stabil** (tanpa token/sementara).

## 🚀 Fitur
* Satu playlist utama: `streams.m3u8` (HLS).
* **Thumbnail otomatis** (`tvg-logo`) per kamera, refresh mingguan.
* Grouping **per kecamatan** biar gampang browse di app IPTV.
* **Dataset uptime harian** (`data/uptime.csv`) + **CHANGELOG** + laporan kualitas (resolusi/bitrate).
* Cek & hapus link mati otomatis (grace 3 hari); kamera yang dihapus otomatis dibuatkan **Issue**.

## 🛠️ Cara Penggunaan
Salin ke VLC / PotPlayer / app IPTV:
```text
https://github.com/akuncadangans1tu-beep/Palembang-CCTV-Streams/raw/refs/heads/main/streams.m3u8
```

### 📱 QR (scan di HP)
![QR](https://api.qrserver.com/v1/create-qr-code/?size=220x220&data=https%3A%2F%2Fgithub.com%2Fakuncadangans1tu-beep%2FPalembang-CCTV-Streams%2Fraw%2Frefs%2Fheads%2Fmain%2Fstreams.m3u8)

## 📊 Status Kamera
<!-- STATUS:START -->
> 🕒 **26 Nov 2026 19:11 WIB** · Total **43** · 🟢 **40** · 🔴 **3**

| Kamera | Grup | Status | Uptime | Kualitas |
|---|---|:--:|:--:|:--:|
| CCTV Bank Sumsel Atmo | Alang-Alang Lebar | 🟢 | 100% | 1920x1080 |
| CCTV Benteng Kuto Besak | Alang-Alang Lebar | 🟢 | 100% | 704x576 |
| CCTV Cinde | Alang-Alang Lebar | 🟢 | 100% | 1920x1080 |
| CCTV JL VETERAN 1 | Alang-Alang Lebar | 🟢 | 100% | 1280x720 |
| CCTV JL VETERAN 2 | Alang-Alang Lebar | 🟢 | 100% | 1280x720 |
| CCTV Lampu Merah Kol Atmo | Alang-Alang Lebar | 🔴 | 50% | 704x576 |
| CCTV Simpang Angkatan 45 | Alang-Alang Lebar | 🟢 | 100% | 704x576 |
| CCTV Simpang Macan Lindungan | Alang-Alang Lebar | 🟢 | 75% | 704x576 |
| CCTV Simpang Polda | Alang-Alang Lebar | 🟢 | 100% | 704x576 |
| CCTV SP BOM BARU | Alang-Alang Lebar | 🟢 | 100% | 1280x720 |
| CCTV SP Soekarno Hatta | Alang-Alang Lebar | 🟢 | 100% | 1920x1080 |
| CCTV JL VETERAN | Bukitkecil | 🟢 | 25% | 1920x1080 |
| CCTV Masjid Agung | Bukitkecil | 🟢 | 100% | 1920x1080 |
| CCTV SP IP | Bukitkecil | 🟢 | 100% | 704x576 |
| CCTV SP Samsat | Bukitkecil | 🟢 | 100% | 1920x1080 |
| CCTV KM 12 | Ilir Timur Dua | 🟢 | 50% | 704x576 |
| CCTV Darma Agung | Ilir Timur Tiga | 🟢 | 100% | 704x576 |
| CCTV Lapangan Parkir Pasar 16 | Ilir Timur Tiga | 🟢 | 100% | 704x576 |
| CCTV SP Charitas | Ilir Timur Tiga | 🔴 | 75% | 1920x1080 |
| CCTV TAMAN SISWA | Ilir Timur Tiga | 🟢 | 100% | 1280x720 |
| CCTV Pasar 16 | Jakabaring | 🟢 | 75% | 704x576 |
| CCTV Plaza 7 Ulu | Jakabaring | 🟢 | 100% | 704x576 |
| CCTV SP BANDARA | Jakabaring | 🟢 | 75% | 1920x1080 |
| CCTV SP DPRD PROV | Jakabaring | 🟢 | 100% | 1920x1080 |
| CCTV SP Parameswara | Jakabaring | 🔴 | 75% | — |
| Lampung 180+000 A | Tol Lampung | 🟢 | 100% | — |
| Lampung 180+000 B | Tol Lampung | 🟢 | 100% | — |
| Lampung 181+000 A | Tol Lampung | 🟢 | 100% | — |
| Lampung 181+000 B | Tol Lampung | 🟢 | 100% | — |
| Palindra 01+600 A | Tol Palindra | 🟢 | 100% | — |
| Palindra 01+600 B | Tol Palindra | 🟢 | 100% | — |
| Palindra 02+600 A | Tol Palindra | 🟢 | 100% | — |
| Palindra 02+600 B | Tol Palindra | 🟢 | 100% | — |
| Palindra 03+600 A | Tol Palindra | 🟢 | 100% | — |
| Palindra 03+600 B | Tol Palindra | 🟢 | 100% | — |
| Palindra 04+600 B | Tol Palindra | 🟢 | 100% | — |
| Palindra 05+600 A | Tol Palindra | 🟢 | 100% | — |
| Palindra 05+600 B | Tol Palindra | 🟢 | 100% | — |
| PALINDRA Gate Pemulutan | Tol Palindra | 🟢 | 100% | — |
| PALINDRA GT Indralaya | Tol Palindra | 🟢 | 100% | — |
| PALINDRA GT KTM RAMBUTAN | Tol Palindra | 🟢 | 100% | — |
| PALINDRA IC KTM | Tol Palindra | 🟢 | 100% | — |
| PALINDRA IC Pemulutan | Tol Palindra | 🟢 | 100% | — |

_🔴 = gagal cek terakhir; dipertahankan maks 3 hari beruntun sebelum dihapus._
<!-- STATUS:END -->

## 📦 Data & Laporan
* [`data/uptime.csv`](data/uptime.csv) — dataset time-series online/offline + kualitas (open data).
* [`CHANGELOG.md`](CHANGELOG.md) — riwayat kamera masuk/keluar.
* [`REPORT.md`](REPORT.md) — laporan run terakhir.
* [`status.json`](status.json) — API mini (JSON) untuk developer.

## 🤖 Cara Kerja Otomatis
Tiap 03:00 WIB GitHub Actions: scrape sumber → kenali/migrasi entri lama → cek HLS (master→media→segmen) → hapus duplikat & yang mati 3 hari beruntun → tulis playlist, dataset, changelog, tabel README. Mingguan: refresh thumbnail via ffmpeg.

## 🤝 Kontribusi
Baca [CONTRIBUTING.md](CONTRIBUTING.md). Pakai template Issue untuk usul kamera baru / lapor kamera mati.
⚠️ **Harus kamera publik di Palembang / koridor tol sekitarnya! Kamera pribadi (kantor, rumah, dll.) dilarang kecuali memang untuk publik.**
