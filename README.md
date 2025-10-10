# ForUS Discord Bot

Bot Discord multifungsi berbahasa Indonesia dengan perintah slash (/) berbasis `discord.py` 2.x dan penyimpanan SQLite asinkron. Dirancang untuk kebutuhan komunitas: moderasi, konfigurasi server, ekonomi, pengingat, tiket dukungan, hingga hiburan ringan.

## Fitur Utama
- ⚙️ **Konfigurasi Slash** `/setup` untuk welcome, goodbye, log, autorole, kategori tiket, dan zona waktu.
- 🛡️ **Moderasi** `/moderasi` (kick/ban/clear/warn) dengan logging otomatis.
- � **Activity Feed** kanal log real-time untuk pesan, edit/hapus, join/leave, voice, perintah, reaksi, dan perubahan struktur server.
- �📊 **Ekonomi & Toko** `/daily`, `/work`, `/transfer`, `/leaderboard`, `/shop list|buy`, serta panel admin `/shopadmin add`.
- ⏰ **Pengingat** `/reminder create|list|delete` dengan scheduler asinkron.
- 🎟️ **Sistem Tiket** `/ticket create|close|add|remove` membuat kanal privat.
- 🎉 **Hiburan** `/meme`, `/quote`, `/joke`, `/dice`, `/8ball`, `/ship`.
- 🤖 **Utilitas** `/ping`, `/help`, `/userinfo`, `/serverinfo`, `/botstats`, `/jadwalsholat`, `/carijadwalsholat`.
- 🕒 **Utilitas Waktu & Zona** `/timestamp` dan `/timezone` untuk membuat kode timestamp Discord dan konversi lintas zona (mendukung alias WIB/WITA/WIT).
- 🧭 **Diagnostik Server** `/roleinfo`, `/channelinfo`, `/serverinfo` (versi terbaru) menyajikan statistik channel, boost, hingga izin penting.
- 🗂️ **Audit Internal** `/audit recent` & `/audit stats` mencatat aktivitas otomatis bot dan ringkasan statistiknya.
- �‍💻 **Developer Insight** `/developer ringkasan` dan `/developer profil` menghadirkan detail tim pengembang, jam support, dan kanal dukungan resmi.
- �👋 **Event Otomatis** sambutan, perpisahan, autorole, dan filter kata kasar + anti-spam sederhana.
- 💑 **Fitur Couple** `/couple propose|respond|status|affection|leaderboard|breakup` lengkap dengan pengaturan anniversary.

## Persiapan Lingkungan
1. Pastikan Python 3.11+ terpasang.
2. Buat virtual environment lalu instal dependensi:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

3. Salin `.env.example` menjadi `.env` dan isi token bot Discord Anda.

## Variabel Lingkungan
| Nama               | Deskripsi                                                |
|--------------------|----------------------------------------------------------|
| `DISCORD_TOKEN`    | Token bot dari portal Discord Developer                  |
| `DISCORD_GUILD_IDS`| Opsional. ID guild pertama untuk sync cepat (debug mode). Jika lebih dari satu ID, hanya yang pertama yang digunakan untuk debug_scope|
| `DATABASE_URL`     | URL database (default `sqlite+aiosqlite:///./bot.db`)    |
| `LOG_LEVEL`        | Level logging (`INFO`, `DEBUG`, dst)                     |
| `OWNER_IDS`        | Opsional. Daftar ID owner (dipisah koma)                 |

## Menjalankan Bot
```bash
python -m bot.main
```

Sinkronisasi perintah slash terjadi otomatis saat bot online:
- **Dengan `DISCORD_GUILD_IDS`**: Sync ke guild pertama (debug_scope) untuk testing lebih cepat (~5-10 detik). Jika multiple guild IDs dikonfigurasi, hanya guild pertama yang digunakan.
- **Tanpa `DISCORD_GUILD_IDS`**: Sync global ke semua server (butuh 1-5 menit). Bot akan cleanup perintah lama yang tidak digunakan.

## Struktur Proyek
```
bot/
  main.py          # Entry point & inisialisasi
  config.py        # Loader konfigurasi .env
  database/        # Lapisan database (core, migrasi, repository)
  services/        # Scheduler, logging, cache
  cogs/            # Kumpulan fitur slash command & listener
  data/            # Data statis (kata terlarang, profil developer)
tests/             # Unit test database dasar
```

## Pengujian
Jalankan seluruh pengujian:

```bash
pytest
```

Tes mencakup lapisan database, utilitas, dan fungsionalitas perintah seperti `/jadwalsholat` maupun `/carijadwalsholat` (dengan mock API). Perintah Discord lain diuji manual melalui staging server.

## Info Developer

Gunakan grup perintah `/developer` untuk mengenal tim pengembang dan kanal dukungan resmi.

- `/developer ringkasan` — menampilkan ringkasan setiap kontributor inti beserta peran dan stack yang digunakan.
- `/developer profil` — memberikan profil lengkap: peran, tanggung jawab, highlight fitur, pencapaian, jam respons, serta tautan kontak.

Setiap informasi bersumber dari berkas statis `bot/data/developers.json` sehingga dapat diperbarui tanpa menyentuh kode. Data ini juga tampil pada perintah `/help` agar mudah ditemukan member server.

## Audit Internal

Gunakan grup perintah `/audit` untuk menelusuri histori otomatis bot seperti penjadwalan pengumuman atau permintaan moderasi:

- `/audit recent` — daftar entri audit terbaru lengkap dengan pelaku, target, konteks, dan stempel waktu relatif.
- `/audit stats` — ringkasan jumlah aksi per kategori dalam rentang hari tertentu beserta daftar aktor teratas.

Seluruh data audit disimpan terpisah dari Audit Log Discord sehingga administrator dapat membaca aktivitas bot tanpa meninggalkan Discord.

## Activity Logger

Aktifkan kanal log aktivitas dengan perintah `/setup log` agar bot dapat mengirim embed ringkas tentang setiap aktivitas penting:

- Pesan baru, suntingan, dan penghapusan (termasuk lampiran).
- Anggota bergabung/keluar, perubahan nickname/role, dan perpindahan voice channel.
- Pembuatan/penghapusan channel, role, serta thread.
- Reaksi yang ditambahkan/dihapus.
- Eksekusi perintah slash maupun prefix beserta error-nya.

Bot otomatis menghindari loop (pesan di kanal log tidak dilaporkan ulang) dan memanfaatkan cache supaya tidak membanjiri database saat mengambil konfigurasi kanal. Jika kanal log dihapus atau bot kehilangan izin, cache dibersihkan otomatis dan Anda akan melihat peringatan pada log server.

## Utilitas Waktu

- `/timestamp` — konversi satu waktu ke tujuh format timestamp Discord siap salin (`<t:..:R>`, `<t:..:F>`, dll) dengan dukungan zona waktu server.
- `/timezone` — konversi lintas zona (bisa lebih dari satu tujuan sekaligus) dengan dukungan alias lokal `WIB/WITA/WIT` serta format offset `UTC±HH:MM`.

## Diagnostik Channel & Role

- `/roleinfo` — tampilkan izin penting, jumlah anggota manusia vs bot, serta metadata lain (warna, posisi, status integrasi).
- `/channelinfo` — detail channel teks, suara, stage, forum, maupun thread: slowmode, auto-archive, bitrate, parent category, dan lainnya.
- `/serverinfo` — versi terbaru menghadirkan statistik anggota, channel, boost, koleksi emoji/stiker, fitur aktif, dan kebijakan keamanan.

## Jadwal Sholat

Gunakan perintah `/jadwalsholat` untuk menampilkan jadwal sholat harian.

- **Negara:** pilih *Indonesia* atau *Malaysia*.
- **Lokasi:**
  - Indonesia: masukkan ID kota empat digit dari dokumentasi [MyQuran API](https://api.myquran.com/) atau pilih dari auto-complete.
  - Malaysia: masukkan kode zon seperti `SGR01` sesuai dokumentasi [WaktuSolat API](https://api.waktusolat.app/) atau pilih dari auto-complete.
- **Tahun/Bulan/Tanggal:** opsional; kosongkan untuk default tanggal hari ini.

Bot akan menampilkan daftar waktu sholat utama dalam embed bersama informasi wilayah dan sumber data.

Untuk mencari ID kota atau kode JAKIM secara cepat, gunakan `/carijadwalsholat`:

- **Negara:** pilih sumber *Indonesia* atau *Malaysia*.
- **Keyword:** ketik nama kota/daerah; minimal dua karakter.
- **Batas:** tentukan jumlah hasil (default 10, maksimal 25).

Bot menampilkan hasil dalam embed siap salin, dan kata kunci yang sama juga tersedia lewat auto-complete `/jadwalsholat`.

## Fitur Couple

Gunakan grup perintah `/couple` untuk membangun interaksi romantis di server:

- `/couple propose` — ajukan pasangan dengan pesan manis opsional. Target akan dapat menjawab melalui `/couple respond`.
- `/couple respond` — terima atau tolak lamaran yang masuk, lengkap dengan pesan balasan privat.
- `/couple status` — lihat status hubungan, tanggal anniversary, dan statistik love points.
- `/couple anniversary set` — atur tanggal spesial kalian dalam format `YYYY-MM-DD`.
- `/couple affection` — klaim love points harian dan bonus sinkron dengan pasangan.
- `/couple leaderboard` — tampilkan papan cinta berdasarkan love points tertinggi di guild.
- `/couple breakup` — akhiri hubungan secara elegan dengan pemberitahuan privat.

Semua data pasangan tersimpan pada database SQLite dan otomatis tersinkron saat bot online.

## Lisensi
Proyek ini dirilis dengan lisensi MIT. Silakan modifikasi sesuai kebutuhan komunitas Anda.
