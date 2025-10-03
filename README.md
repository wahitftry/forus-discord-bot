# Nusantara Discord Bot

Bot Discord multifungsi berbahasa Indonesia dengan perintah slash (/) berbasis `discord.py` 2.x dan penyimpanan SQLite asinkron. Dirancang untuk kebutuhan komunitas: moderasi, konfigurasi server, ekonomi, pengingat, tiket dukungan, hingga hiburan ringan.

## Fitur Utama
- ⚙️ **Konfigurasi Slash** `/setup` untuk welcome, goodbye, log, autorole, kategori tiket, dan zona waktu.
- 🛡️ **Moderasi** `/moderasi` (kick/ban/clear/warn) dengan logging otomatis.
- 📊 **Ekonomi & Toko** `/daily`, `/work`, `/transfer`, `/leaderboard`, `/shop list|buy`, serta panel admin `/shopadmin add`.
- ⏰ **Pengingat** `/reminder create|list|delete` dengan scheduler asinkron.
- 🎟️ **Sistem Tiket** `/ticket create|close|add|remove` membuat kanal privat.
- 🎉 **Hiburan** `/meme`, `/quote`, `/joke`, `/dice`, `/8ball`, `/ship`.
- 🤖 **Utilitas** `/ping`, `/help`, `/userinfo`, `/serverinfo`, `/botstats`.
- 👋 **Event Otomatis** sambutan, perpisahan, autorole, dan filter kata kasar + anti-spam sederhana.

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
  data/            # Data statis (kata terlarang)
tests/             # Unit test database dasar
```

## Pengujian
Jalankan seluruh pengujian:

```bash
pytest
```

Tes fokus pada lapisan database dan utilitas; perintah Discord diuji manual melalui staging server.

## Lisensi
Proyek ini dirilis dengan lisensi MIT. Silakan modifikasi sesuai kebutuhan komunitas Anda.
