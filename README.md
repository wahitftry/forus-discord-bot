# Nusantara Discord Bot

Bot Discord multifungsi berbahasa Indonesia dengan perintah slash (/) berbasis `discord.py` 2.x dan penyimpanan SQLite asinkron. Dirancang untuk kebutuhan komunitas: moderasi, konfigurasi server, ekonomi, pengingat, tiket dukungan, hingga hiburan ringan.

## Fitur Utama
- ⚙️ **Konfigurasi Slash** `/setup` untuk welcome, goodbye, log, autorole, kategori tiket, dan zona waktu.
- 🛡️ **Moderasi** `/moderasi` (kick/ban/clear/warn) dengan logging otomatis.
- 📊 **Ekonomi & Toko** `/daily`, `/work`, `/transfer`, `/leaderboard`, `/shop list|buy`, serta panel admin `/shopadmin add`.
- ⏰ **Pengingat** `/reminder create|list|delete` dengan scheduler asinkron.
- 🎟️ **Sistem Tiket** `/ticket create|close|add|remove` membuat kanal privat.
- 🎉 **Hiburan** `/meme`, `/quote`, `/joke`, `/dice`, `/8ball`, `/ship`.
- 🤖 **Utilitas** `/ping`, `/help`, `/userinfo`, `/serverinfo`, `/botstats`, `/jadwalsholat`, `/carijadwalsholat`.
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
| `DISCORD_GUILD_IDS`| Opsional. Daftar ID guild (dipisah koma) untuk sync cepat|
| `DATABASE_URL`     | URL database (default `sqlite+aiosqlite:///./bot.db`)    |
| `LOG_LEVEL`        | Level logging (`INFO`, `DEBUG`, dst)                     |
| `OWNER_IDS`        | Opsional. Daftar ID owner (dipisah koma)                 |

## Menjalankan Bot
```bash
python -m bot.main
```

Sinkronisasi perintah slash terjadi otomatis saat bot online. Jika `DISCORD_GUILD_IDS` diisi, sync hanya ke guild tersebut (lebih cepat). Tanpa itu, bot akan membersihkan perintah khusus guild yang tersisa dan hanya mendaftarkan ulang perintah global (butuh beberapa menit).

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
