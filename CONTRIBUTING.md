# Kontribusi

Terima kasih mau bantu! 🙌

## Aturan kamera
- **Publik & legal**: hanya kamera yang memang disiarkan untuk umum oleh pemiliknya.
- **Wilayah**: Palembang dan koridor tol sekitarnya (Palindra / Lampung / JTTS).
- **Stabil**: HLS `.m3u8` langsung, **tanpa token / tanda tangan / proxy sementara**.
- **Bukan kamera pribadi** (kantor, rumah, kamar) kecuali memang dipublikasikan untuk umum.

## Cara usul kamera baru
1. Buka **Issues → New issue → "Usul kamera baru"**, isi form.
2. Sertakan URL `.m3u8` dan sumber resminya.
3. Maintainer akan verifikasi stabilitas sebelum menambah ke `OPENCCTV_REGIONS` / scraper.

## Lapor kamera mati
Buka **Issues → "Lapor kamera mati"**. Checker juga otomatis membuat issue saat menghapus kamera.

##Development lokal
```bash
python scripts/update_streams.py --dry-run --limit 3   # tes cepat, tidak menulis
python scripts/update_streams.py                       # run penuh
python scripts/update_streams.py --thumbs              # butuh ffmpeg
