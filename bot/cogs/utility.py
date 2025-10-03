from __future__ import annotations

import calendar
import platform
import time
from datetime import date, datetime
from typing import TYPE_CHECKING, Any
from urllib.parse import quote_plus
from zoneinfo import ZoneInfo

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands

from bot.services.cache import TTLCache

if TYPE_CHECKING:
    from bot.main import ForUS


PRAYER_CACHE_TTL = 60 * 60 * 6
LOOKUP_CACHE_TTL = 60 * 60 * 12
INDONESIA_TIMEZONE = ZoneInfo("Asia/Jakarta")
MALAYSIA_TIMEZONE = ZoneInfo("Asia/Kuala_Lumpur")


class PrayerAPIError(RuntimeError):
    """Kesalahan umum ketika mengambil data jadwal sholat."""


class Utility(commands.Cog):
    def __init__(self, bot: ForUS) -> None:
        self.bot = bot
        self.launch_time = time.time()
        self.session = aiohttp.ClientSession()
        self.prayer_cache = TTLCache(ttl=PRAYER_CACHE_TTL)
        self.lookup_cache = TTLCache(ttl=LOOKUP_CACHE_TTL)

    async def cog_unload(self) -> None:
        await self.session.close()

    @app_commands.command(name="ping", description="Cek latensi bot.")
    async def ping(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message(
            f"Pong! Latensi gateway: {self.bot.latency * 1000:.0f} ms",
            ephemeral=True,
        )

    @app_commands.command(name="help", description="Daftar perintah bot.")
    async def help(self, interaction: discord.Interaction) -> None:
        embed = discord.Embed(
            title="Panduan Perintah",
            description="Berikut beberapa perintah utama. Gunakan auto-complete di Discord untuk melihat semua perintah.",
            color=discord.Color.blurple(),
        )
        embed.add_field(name="/ping", value="Menampilkan latensi bot.", inline=False)
        embed.add_field(name="/userinfo", value="Informasi dasar pengguna.", inline=False)
        embed.add_field(name="/serverinfo", value="Ringkasan server.", inline=False)
        embed.add_field(name="/botstats", value="Statistik bot & uptime.", inline=False)
        embed.add_field(name="/jadwalsholat", value="Tampilkan jadwal sholat harian untuk Indonesia atau Malaysia.", inline=False)
        embed.add_field(name="/carijadwalsholat", value="Cari ID kota (Indonesia) atau kode JAKIM zona (Malaysia).", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="carijadwalsholat", description="Cari ID kota (Indonesia) atau kode JAKIM (Malaysia) untuk jadwal sholat.")
    @app_commands.describe(
        negara="Pilih negara sumber data",
        keyword="Ketik nama kota/zona yang ingin dicari",
        batas="Batas jumlah hasil (1-25)",
    )
    @app_commands.choices(
        negara=[
            app_commands.Choice(name="Indonesia", value="indonesia"),
            app_commands.Choice(name="Malaysia", value="malaysia"),
        ]
    )
    async def carijadwalsholat(
        self,
        interaction: discord.Interaction,
        negara: app_commands.Choice[str],
        keyword: str,
        batas: app_commands.Range[int, 1, 25] = 10,
    ) -> None:
        keyword = keyword.strip()
        if len(keyword) < 2:
            await interaction.response.send_message(
                "Masukkan minimal 2 karakter untuk melakukan pencarian.",
                ephemeral=True,
            )
            return

        batas = int(batas)

        try:
            if negara.value == "indonesia":
                results = await self._search_indonesia_locations(keyword)
                limited = results[:batas]
                embed = self._build_search_embed_indonesia(keyword, limited)
            else:
                results = await self._search_malaysia_zones(keyword)
                limited = results[:batas]
                embed = self._build_search_embed_malaysia(keyword, limited)
        except PrayerAPIError as exc:
            await interaction.response.send_message(str(exc), ephemeral=True)
            return

        if not limited:
            await interaction.response.send_message(
                "Tidak ada hasil yang cocok. Coba kata kunci lain.",
                ephemeral=True,
            )
            return

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="userinfo", description="Menampilkan info pengguna.")
    async def userinfo(self, interaction: discord.Interaction, user: discord.User | None = None) -> None:
        user = user or interaction.user
        embed = discord.Embed(title=f"Info {user.display_name}", color=discord.Color.green())
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.add_field(name="ID", value=str(user.id))
        embed.add_field(name="Bot?", value="Ya" if user.bot else "Tidak")
        embed.add_field(name="Dibuat", value=discord.utils.format_dt(user.created_at, style="F"), inline=False)
        if isinstance(user, discord.Member):
            embed.add_field(name="Bergabung", value=discord.utils.format_dt(user.joined_at, style="F"), inline=False)
            roles = ", ".join(role.mention for role in user.roles[1:]) or "Tidak ada"
            embed.add_field(name="Role", value=roles, inline=False)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="serverinfo", description="Menampilkan info server.")
    async def serverinfo(self, interaction: discord.Interaction) -> None:
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message("Perintah ini hanya dapat digunakan dalam server.", ephemeral=True)
            return
        embed = discord.Embed(title=guild.name, color=discord.Color.gold())
        embed.set_thumbnail(url=guild.icon.url if guild.icon else discord.Embed.Empty)
        embed.add_field(name="ID", value=str(guild.id))
        embed.add_field(name="Owner", value=guild.owner.mention if guild.owner else "Tidak diketahui")
        embed.add_field(name="Anggota", value=str(guild.member_count))
        embed.add_field(name="Dibuat", value=discord.utils.format_dt(guild.created_at, style="F"), inline=False)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="botstats", description="Statistik bot singkat.")
    async def botstats(self, interaction: discord.Interaction) -> None:
        uptime = time.time() - self.launch_time
        uptime_hours = uptime / 3600
        embed = discord.Embed(title="Statistik Bot", color=discord.Color.purple())
        embed.add_field(name="Versi Python", value=platform.python_version())
        embed.add_field(name="Versi Discord.py", value=discord.__version__)
        embed.add_field(name="Total Guild", value=str(len(self.bot.guilds)))
        embed.add_field(name="Total Pengguna", value=str(len(self.bot.users)))
        embed.add_field(name="Uptime", value=f"{uptime_hours:.2f} jam")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="jadwalsholat", description="Menampilkan jadwal sholat harian berdasarkan negara.")
    @app_commands.describe(
        negara="Pilih negara sumber jadwal.",
        lokasi="Masukkan ID kota (Indonesia) atau kode zona (Malaysia).",
        tahun="Tahun dalam format YYYY. Jika kosong, memakai tahun saat ini.",
        bulan="Nomor bulan (1-12). Jika kosong, memakai bulan saat ini.",
        tanggal="Tanggal dalam bulan (1-31). Jika kosong, memakai hari ini.",
    )
    @app_commands.choices(
        negara=[
            app_commands.Choice(name="Indonesia", value="indonesia"),
            app_commands.Choice(name="Malaysia", value="malaysia"),
        ]
    )
    async def jadwalsholat(
        self,
        interaction: discord.Interaction,
        negara: app_commands.Choice[str],
        lokasi: str,
        tahun: int | None = None,
        bulan: int | None = None,
        tanggal: int | None = None,
    ) -> None:
        try:
            target_date = self._build_target_date(negara.value, tahun, bulan, tanggal)
        except PrayerAPIError as exc:
            await interaction.response.send_message(str(exc), ephemeral=True)
            return

        try:
            if negara.value == "indonesia":
                month_payload = await self._fetch_month_indonesia(lokasi, target_date.year, target_date.month)
                day_payload = self._extract_indonesia_day(month_payload, target_date)
                embed = self._build_embed_indonesia(lokasi, month_payload, day_payload)
            else:
                month_payload = await self._fetch_month_malaysia(lokasi, target_date.year, target_date.month)
                day_payload = self._extract_malaysia_day(month_payload, target_date)
                embed = self._build_embed_malaysia(lokasi, target_date, month_payload, day_payload)
        except PrayerAPIError as exc:
            if interaction.response.is_done():
                await interaction.followup.send(str(exc), ephemeral=True)
            else:
                await interaction.response.send_message(str(exc), ephemeral=True)
            return
        except Exception:  # noqa: BLE001
            logger = getattr(self.bot, "log", None)
            if logger:
                logger.exception("Gagal mengambil jadwal sholat")
            message = "Terjadi kesalahan saat mengambil jadwal sholat. Coba lagi nanti."
            if interaction.response.is_done():
                await interaction.followup.send(message, ephemeral=True)
            else:
                await interaction.response.send_message(message, ephemeral=True)
            return

        if interaction.response.is_done():
            await interaction.followup.send(embed=embed)
        else:
            await interaction.response.send_message(embed=embed)

    @jadwalsholat.autocomplete("lokasi")
    async def jadwalsholat_lokasi_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> list[app_commands.Choice[str]]:
        current = current.strip()
        if len(current) < 2:
            return []

        negara_choice = getattr(interaction.namespace, "negara", None)
        if not negara_choice:
            return []

        negara_value = getattr(negara_choice, "value", negara_choice)

        try:
            if negara_value == "indonesia":
                results = await self._search_indonesia_locations(current)
                choices = [
                    app_commands.Choice(name=self._truncate_label(f"{item.get('lokasi', 'Tidak diketahui')} ({item.get('id')})"), value=str(item.get("id")))
                    for item in results[:25]
                ]
            elif negara_value == "malaysia":
                results = await self._search_malaysia_zones(current)
                choices = []
                for item in results[:25]:
                    code = item.get("jakimCode", "-")
                    negeri = item.get("negeri", "")
                    daerah = item.get("daerah", "")
                    label = f"{code} • {negeri}" if negeri else code
                    if daerah:
                        label = f"{label} – {daerah}"
                    choices.append(app_commands.Choice(name=self._truncate_label(label), value=str(code)))
            else:
                return []
        except PrayerAPIError:
            return []

        return choices

    def _build_target_date(
        self,
        negara: str,
        tahun: int | None,
        bulan: int | None,
        tanggal: int | None,
    ) -> date:
        timezone = INDONESIA_TIMEZONE if negara == "indonesia" else MALAYSIA_TIMEZONE
        today = datetime.now(timezone).date()
        year = tahun or today.year
        month = bulan or today.month
        if not 1 <= month <= 12:
            raise PrayerAPIError("Bulan harus di antara 1-12.")
        max_day = calendar.monthrange(year, month)[1]
        day = tanggal or today.day
        if not 1 <= day <= max_day:
            raise PrayerAPIError(f"Tanggal harus di antara 1-{max_day} untuk bulan tersebut.")
        return date(year, month, day)

    async def _fetch_month_indonesia(self, kota_id: str, year: int, month: int) -> dict[str, Any]:
        cache_key = f"id:{kota_id}:{year}:{month:02d}"

        async def _factory() -> dict[str, Any]:
            url = f"https://api.myquran.com/v2/sholat/jadwal/{kota_id}/{year}/{month:02d}"
            payload = await self._request_json(url)
            if not payload.get("status"):
                message = payload.get("message", "Permintaan tidak berhasil.")
                raise PrayerAPIError(f"API MyQuran: {message}")
            data = payload.get("data")
            if not data or "jadwal" not in data:
                raise PrayerAPIError("Data jadwal Indonesia tidak ditemukan.")
            return data

        return await self.prayer_cache.get_or_set(cache_key, _factory)

    async def _fetch_month_malaysia(self, zone_code: str, year: int, month: int) -> dict[str, Any]:
        cache_key = f"my:{zone_code}:{year}:{month:02d}"

        async def _factory() -> dict[str, Any]:
            url = f"https://api.waktusolat.app/v2/solat/{zone_code}?year={year}&month={month}"
            payload = await self._request_json(url)
            if "prayers" not in payload:
                raise PrayerAPIError("Data jadwal Malaysia tidak ditemukan.")
            zone_detail = await self._get_malaysia_zone_detail(zone_code)
            if zone_detail:
                payload["zone_detail"] = zone_detail
            return payload

        return await self.prayer_cache.get_or_set(cache_key, _factory)

    async def _search_indonesia_locations(self, keyword: str) -> list[dict[str, Any]]:
        normalized = keyword.strip()
        if len(normalized) < 2:
            return []

        cache_key = f"lookup:id:{normalized.lower()}"

        async def _factory() -> list[dict[str, Any]]:
            encoded = quote_plus(normalized)
            url = f"https://api.myquran.com/v2/sholat/kota/cari/{encoded}"
            payload = await self._request_json(url)
            if not payload.get("status", True):
                message = payload.get("message", "Permintaan tidak berhasil.")
                raise PrayerAPIError(f"API MyQuran: {message}")
            data = payload.get("data") or []
            if not isinstance(data, list):
                raise PrayerAPIError("Data kota Indonesia tidak valid.")
            return data

        results = await self.lookup_cache.get_or_set(cache_key, _factory)
        return list(results)

    async def _search_malaysia_zones(self, keyword: str) -> list[dict[str, Any]]:
        normalized = keyword.strip()
        if len(normalized) < 2:
            return []
        zones = await self._get_malaysia_zones()
        keyword_lower = normalized.lower()
        filtered: list[dict[str, Any]] = []
        for zone in zones:
            code = str(zone.get("jakimCode", "")).lower()
            negeri = str(zone.get("negeri", "")).lower()
            daerah = str(zone.get("daerah", "")).lower()
            if keyword_lower in code or keyword_lower in negeri or keyword_lower in daerah:
                filtered.append(zone)
        return filtered

    async def _get_malaysia_zones(self) -> list[dict[str, Any]]:

        async def _factory() -> list[dict[str, Any]]:
            payload = await self._request_json("https://api.waktusolat.app/zones")
            if not isinstance(payload, list):
                raise PrayerAPIError("Data zona Malaysia tidak valid.")
            return payload

        zones = await self.lookup_cache.get_or_set("lookup:my:zones", _factory)
        return list(zones)

    async def _get_malaysia_zone_detail(self, zone_code: str) -> dict[str, Any] | None:
        zone_code_upper = zone_code.upper()
        zones = await self._get_malaysia_zones()
        for zone in zones:
            if str(zone.get("jakimCode", "")).upper() == zone_code_upper:
                return zone
        return None

    def _build_search_embed_indonesia(self, keyword: str, results: list[dict[str, Any]]) -> discord.Embed:
        embed = discord.Embed(
            title="Pencarian Kota Jadwal Sholat (Indonesia)",
            description=f"Kata kunci: `{keyword}`",
            color=discord.Color.blue(),
        )
        if not results:
            embed.add_field(name="Hasil", value="Tidak ditemukan kota yang cocok.", inline=False)
            embed.set_footer(text="Sumber: api.myquran.com")
            return embed

        for item in results:
            lokasi = item.get("lokasi", "Tidak diketahui")
            kota_id = item.get("id", "-")
            embed.add_field(name=str(lokasi), value=f"ID Kota: `{kota_id}`", inline=False)

        embed.set_footer(text="Sumber: api.myquran.com")
        return embed

    def _build_search_embed_malaysia(self, keyword: str, results: list[dict[str, Any]]) -> discord.Embed:
        embed = discord.Embed(
            title="Pencarian Zona JAKIM (Malaysia)",
            description=f"Kata kunci: `{keyword}`",
            color=discord.Color.dark_teal(),
        )
        if not results:
            embed.add_field(name="Hasil", value="Tidak ditemukan zona yang cocok.", inline=False)
            embed.set_footer(text="Sumber: api.waktusolat.app")
            return embed

        for zone in results:
            code = zone.get("jakimCode", "-")
            negeri = zone.get("negeri", "")
            daerah = zone.get("daerah", "")
            title = f"{code} • {negeri}" if negeri else str(code)
            value_parts = []
            if daerah:
                value_parts.append(daerah)
            embed.add_field(name=title, value="\n".join(value_parts) or "Tidak ada detail daerah", inline=False)

        embed.set_footer(text="Sumber: api.waktusolat.app")
        return embed

    async def _request_json(self, url: str) -> Any:
        try:
            async with self.session.get(url, timeout=15) as response:
                if response.status >= 400:
                    raise PrayerAPIError(f"Permintaan ke API gagal dengan status {response.status}.")
                return await response.json()
        except aiohttp.ClientError as exc:  # noqa: PERF203
            raise PrayerAPIError("Tidak dapat terhubung ke layanan jadwal sholat.") from exc

    def _extract_indonesia_day(self, payload: dict[str, Any], target_date: date) -> dict[str, Any]:
        for item in payload.get("jadwal", []):
            if item.get("date") == target_date.isoformat():
                return item
        raise PrayerAPIError("Jadwal untuk tanggal tersebut tidak tersedia pada API MyQuran.")

    def _extract_malaysia_day(self, payload: dict[str, Any], target_date: date) -> dict[str, Any]:
        day_number = target_date.day
        for item in payload.get("prayers", []):
            if item.get("day") == day_number:
                return item
        raise PrayerAPIError("Jadwal untuk tanggal tersebut tidak tersedia pada API WaktuSolat.")

    def _build_embed_indonesia(
        self,
        kota_id: str,
        month_payload: dict[str, Any],
        day_payload: dict[str, Any],
    ) -> discord.Embed:
        lokasi = month_payload.get("lokasi", kota_id)
        daerah = month_payload.get("daerah")
        judul = f"Jadwal Sholat • {lokasi.title() if isinstance(lokasi, str) else lokasi}"
        deskripsi = day_payload.get("tanggal") or day_payload.get("date") or ""
        if daerah:
            deskripsi += f"\n{daerah.title() if isinstance(daerah, str) else daerah}"

        embed = discord.Embed(title=judul, description=deskripsi.strip(), color=discord.Color.teal())
        for nama, key in [
            ("Imsak", "imsak"),
            ("Subuh", "subuh"),
            ("Terbit", "terbit"),
            ("Dhuha", "dhuha"),
            ("Dzuhur", "dzuhur"),
            ("Ashar", "ashar"),
            ("Maghrib", "maghrib"),
            ("Isya", "isya"),
        ]:
            value = day_payload.get(key)
            if value:
                embed.add_field(name=nama, value=value, inline=True)

        embed.set_footer(text=f"Sumber: api.myquran.com • ID Kota: {kota_id}")
        return embed

    def _build_embed_malaysia(
        self,
        zone_code: str,
        target_date: date,
        month_payload: dict[str, Any],
        day_payload: dict[str, Any],
    ) -> discord.Embed:
        zone_detail = month_payload.get("zone_detail")
        readable_label = None
        daerah = None
        if isinstance(zone_detail, dict):
            negeri = str(zone_detail.get("negeri", "")).strip()
            daerah = str(zone_detail.get("daerah", "")).strip() or None
            parts = [part for part in [negeri] if part]
            if parts:
                readable_label = parts[0]

        if not readable_label:
            readable_label = str(month_payload.get("zone", zone_code))

        judul = f"Jadwal Solat • {readable_label}"

        deskripsi_lines = [target_date.strftime("%A, %d %B %Y")]
        if daerah:
            deskripsi_lines.append(daerah)
        deskripsi = "\n".join(deskripsi_lines)
        embed = discord.Embed(title=judul, description=deskripsi, color=discord.Color.green())

        tz = MALAYSIA_TIMEZONE

        def format_epoch(key: str) -> str:
            raw = day_payload.get(key)
            if raw is None:
                raise PrayerAPIError("Data waktu solat tidak valid.")
            dt = datetime.fromtimestamp(raw, tz)
            return dt.strftime("%H:%M")

        label_map = [
            ("Subuh", "fajr"),
            ("Syuruk", "syuruk"),
            ("Dzuhur", "dhuhr"),
            ("Ashar", "asr"),
            ("Maghrib", "maghrib"),
            ("Isya", "isha"),
        ]

        for label, key in label_map:
            embed.add_field(name=label, value=format_epoch(key), inline=True)

        hijri = day_payload.get("hijri")
        if hijri:
            embed.add_field(name="Tanggal Hijriah", value=hijri, inline=False)
        embed.set_footer(text=f"Sumber: api.waktusolat.app • Zona JAKIM: {zone_code}")
        return embed

    def _truncate_label(self, text: str, limit: int = 95) -> str:
        if len(text) <= limit:
            return text
        return text[: limit - 1] + "…"


async def setup(bot: ForUS) -> None:
    await bot.add_cog(Utility(bot))
