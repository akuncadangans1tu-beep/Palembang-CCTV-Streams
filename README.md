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
_Tabel dibuat otomatis pada run pertama._
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
