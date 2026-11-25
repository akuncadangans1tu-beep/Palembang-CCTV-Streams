# 📹 Palembang CCTV Streams (Unofficial)

[![Update CCTV Streams](https://github.com/akuncadangans1tu-beep/Palembang-CCTV-Streams/actions/workflows/update-streams.yml/badge.svg)](https://github.com/akuncadangans1tu-beep/Palembang-CCTV-Streams/actions/workflows/update-streams.yml)

Daftar putar (*playlist*) aliran video CCTV langsung dari berbagai sudut Kota Palembang dan koridor jalan tol sekitarnya, mirip konsep IPTV-Org. Semua tautan HLS (`.m3u8`) stabil, diperiksa & diperbarui **otomatis setiap hari**.

## 🚧 Status Proyek

Playlist ini **dirawat otomatis** tiap hari. Sebagian kamera bisa offline sesaat (wajar, biasanya pulih sendiri), dan cakupan kamera terus bertambah bertahap.

## ⚠️ Disclaimer Penting (Sanggahan)

Proyek ini adalah pengembangan independen dan **tidak memiliki hubungan resmi** dengan instansi pemerintah mana pun.

* **Bukan Produk DisHub**: Proyek ini **tidak** bekerja sama, **tidak** didukung, dan **tidak** menggunakan server internal milik Dinas Perhubungan (DisHub).
* **Tidak Terafiliasi dengan Gubernur**: Proyek ini **tidak** terikat dengan Gubernur Sumatera Selatan atau Pemerintah Kota Palembang.
* **Sumber Data**: Seluruh tautan *stream* diambil dari sumber publik yang tersedia secara terbuka di internet.

## 📡 Sumber

| Sumber | Cakupan |
|---|---|
| `cctv.palembang.go.id` (API publik) | Kamera kota Palembang (Diskominfo & Dishub) |
| `opencctv.org` → `pub.hk-opt.com` (Hutama Karya) | Kamera Tol Palindra & Tol Lampung (JTTS) |

Hanya tautan HLS langsung yang **stabil** (tanpa token/sementara) yang dimasukkan.

## 🚀 Fitur Utama

* Tautan *stream* langsung dari jalan protokol Palembang dan jalan tol sekitarnya.
* **Aplikasi web** (GitHub Pages): galeri video, peta kamera, pencarian, tombol acak.
* **Pembaruan otomatis tiap hari** (03:00 WIB): cek stream, perbarui URL, hapus yang mati 3 hari beruntun.
* **Riwayat uptime** per kamera + tabel status live/offline di bawah ini.

## 🛠️ Cara Penggunaan

Putar dengan VLC, PotPlayer, atau aplikasi IPTV lainnya. Salin tautan ini:

```text
https://github.com/akuncadangans1tu-beep/Palembang-CCTV-Streams/raw/refs/heads/main/streams.m3u8
