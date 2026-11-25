# 📹 Palembang CCTV Streams (Unofficial)

![Update CCTV Streams](https://github.com/akuncadangans1tu-beep/Palembang-CCTV-Streams/actions/workflows/update-streams.yml/badge.svg)

Daftar putar (*playlist*) aliran video CCTV langsung dari berbagai sudut Kota Palembang dan koridor jalan tol sekitarnya, mirip dengan konsep proyek IPTV-Org. Semua tautan berupa HLS (`.m3u8`) stabil yang diperiksa dan diperbarui **otomatis setiap hari**.

## 🚧 Status Proyek

Playlist ini **dirawat otomatis** tiap hari (cek, perbarui, dan hapus tautan mati). Meski begitu:
* Sebagian kamera bisa offline sesaat (pemeliharaan/gangguan) — wajar dan biasanya pulih sendiri.
* Cakupan kamera masih terus bertambah secara bertahap.

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
* Format ramah pemutar video m3u/m3u8 (HLS).
* **Pembaruan otomatis tiap hari** (03:00 WIB) via GitHub Actions: cek kesehatan stream, perbarui URL yang berubah, hapus yang mati 3 hari berturut-turut.
* Tabel status kamera live/offline di bawah ini, ikut diperbarui otomatis.

## 🛠️ Cara Penggunaan

Anda dapat memutar daftar CCTV ini menggunakan pemutar video favorit Anda seperti VLC, PotPlayer, atau aplikasi IPTV Player lainnya. Salin tautan di bawah ini:

```text
https://github.com/akuncadangans1tu-beep/Palembang-CCTV-Streams/raw/refs/heads/main/streams.m3u8
