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
* Playlist utama + **pecahan** (kota / tol) + varian `.m3u`.
* **Thumbnail otomatis** (`tvg-logo`) per kamera, refresh mingguan.
* Grouping **per kecamatan** biar gampang browse di app IPTV.
* **Dataset uptime harian** (`data/uptime.csv`) + **CHANGELOG** + laporan kualitas (resolusi/bitrate).
* Cek & hapus link mati otomatis (grace 3 hari); kamera yang dihapus otomatis dibuatkan **Issue**.

## 🛠️ Cara Penggunaan
Salin ke VLC / PotPlayer / app IPTV:
```text
https://github.com/akuncadangans1tu-beep/Palembang-CCTV-Streams/raw/refs/heads/main/streams.m3u8
