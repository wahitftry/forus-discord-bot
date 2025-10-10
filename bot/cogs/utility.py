from __future__ import annotations

import calendar
import platform
import time
from datetime import date, datetime, timezone as dt_timezone
from typing import TYPE_CHECKING, Any
from urllib.parse import quote_plus
from zoneinfo import ZoneInfo

import aiohttp
import interactions

from bot.services.cache import TTLCache
from bot.services.utility_tools import (
    discord_timestamp_variants,
    format_timezone_display,
    gather_guild_statistics,
    parse_datetime_input,
    process_resource_snapshot,
    resolve_timezone,
)

if TYPE_CHECKING:
    from bot.main import ForUS


PRAYER_CACHE_TTL = 60 * 60 * 6
LOOKUP_CACHE_TTL = 60 * 60 * 12
INDONESIA_TIMEZONE = ZoneInfo("Asia/Jakarta")
MALAYSIA_TIMEZONE = ZoneInfo("Asia/Kuala_Lumpur")


def format_dt(dt: datetime, style: str = 'f') -> str:
    """Format datetime as Discord timestamp."""
    return interactions.Timestamp.fromdatetime(dt).format(interactions.TimestampStyles(style.upper()))


class PrayerAPIError(RuntimeError):
    """Kesalahan umum ketika mengambil data jadwal sholat."""


class Utility(interactions.Extension):
    def __init__(self, bot: ForUS) -> None:
        self.bot = bot
        self.launch_time = time.time()
        self.session = aiohttp.ClientSession()
        self.prayer_cache = TTLCache(ttl=PRAYER_CACHE_TTL)
        self.lookup_cache = TTLCache(ttl=LOOKUP_CACHE_TTL)

    def drop(self) -> None:
        import asyncio
        asyncio.create_task(self.session.close())

    async def _get_default_timezone(self, guild: interactions.Guild | None) -> str:
        if guild and self.bot.guild_repo is not None:
            settings = await self.bot.guild_repo.get(guild.id)
            if settings and settings.timezone:
                return settings.timezone
        return "Asia/Jakarta"

    @staticmethod
    def _highlight_permissions(role: interactions.Role) -> str:
        important = [
            ("administrator", "Administrator"),
            ("manage_guild", "Kelola Server"),
            ("manage_roles", "Kelola Role"),
            ("manage_channels", "Kelola Channel"),
            ("ban_members", "Ban Member"),
            ("kick_members", "Kick Member"),
            ("moderate_members", "Timeout"),
            ("manage_messages", "Kelola Pesan"),
            ("mention_everyone", "Mention Everyone"),
            ("manage_webhooks", "Kelola Webhook"),
        ]
        granted = [label for attr, label in important if getattr(role.permissions, attr, False)]
        return ", ".join(granted) if granted else "Tidak ada"

    @staticmethod
    def _limit_text(value: str | None, limit: int = 200) -> str | None:
        if value is None:
            return None
        if len(value) <= limit:
            return value
        return value[: limit - 3] + "..."

    @interactions.slash_command(name='ping', description='Cek latensi bot.')
    async def ping(self, ctx: interactions.SlashContext) -> None:
        await ctx.send(
            f"Pong! Latensi gateway: {self.bot.latency * 1000:.0f} ms",
            ephemeral=True,
        )

    @interactions.slash_command(name='help', description='Daftar perintah bot.')
    async def help(self, ctx: interactions.SlashContext) -> None:
        embed = interactions.Embed(
            title="Panduan Perintah",
            description="Berikut beberapa perintah utama. Gunakan auto-complete di Discord untuk melihat semua perintah.",
            color=interactions.Color.blurple(),
        )
        embed.add_field(name="/ping", value="Menampilkan latensi bot.", inline=False)
        embed.add_field(name="/userinfo", value="Informasi dasar pengguna.", inline=False)
        embed.add_field(name="/serverinfo", value="Ringkasan server.", inline=False)
        embed.add_field(name="/botstats", value="Statistik bot & uptime.", inline=False)
        embed.add_field(name="/timestamp", value="Konversi waktu menjadi berbagai format timestamp Discord.", inline=False)
        embed.add_field(name="/timezone", value="Konversi waktu antar zona secara cepat (mendukung beberapa target).", inline=False)
        embed.add_field(name="/roleinfo", value="Tampilkan detail role, izin penting, dan jumlah anggotanya.", inline=False)
        embed.add_field(name="/channelinfo", value="Diagnostik channel teks/suara/thread termasuk slowmode, NSFW, dan lainnya.", inline=False)
        embed.add_field(name="/developer ringkasan", value="Profil singkat tim pengembang.", inline=False)
        embed.add_field(name="/developer profil", value="Detail lengkap developer tertentu.", inline=False)
        embed.add_field(name="/jadwalsholat", value="Tampilkan jadwal sholat harian untuk Indonesia atau Malaysia.", inline=False)
        embed.add_field(name="/carijadwalsholat", value="Cari ID kota (Indonesia) atau kode JAKIM zona (Malaysia).", inline=False)
        embed.add_field(name="/audit recent", value="Ringkasan aktivitas penting dari log audit internal.", inline=False)
        embed.add_field(name="/audit stats", value="Statistik frekuensi aksi audit dalam rentang waktu tertentu.", inline=False)
        await ctx.send(embed=embed, ephemeral=True)

    @interactions.slash_command(name='timestamp', description='Konversi waktu menjadi berbagai format timestamp Discord siap pakai.')
    @interactions.slash_option(
        name="waktu",
        description="Waktu target (contoh: 2025-01-31 19:30)",
        opt_type=interactions.OptionType.STRING,
        required=True,
    )
    @interactions.slash_option(
        name="zona_waktu",
        description="Zona waktu asal. Kosongkan untuk mengikuti pengaturan server atau Asia/Jakarta.",
        opt_type=interactions.OptionType.STRING,
        required=False,
    )
    async def timestamp(self, ctx: interactions.SlashContext, waktu: str, zona_waktu: str | None = None) -> None:
        default_tz_name = await self._get_default_timezone(ctx.guild)
        try:
            source_tz = resolve_timezone(zona_waktu, fallback=default_tz_name)
        except ValueError as exc:
            await ctx.send(str(exc), ephemeral=True)
            return

        try:
            local_dt = parse_datetime_input(waktu, source_tz)
        except ValueError as exc:
            await ctx.send(str(exc), ephemeral=True)
            return

        utc_dt = local_dt.astimezone(dt_timezone.utc)
        variants = discord_timestamp_variants(local_dt)
        embed = interactions.Embed(
            title="Format Timestamp Discord",
            description=(
                f"Waktu sumber: {format_dt(local_dt, style='F')}\n"
                f"Zona waktu: {format_timezone_display(source_tz)}"
            ),
            color=interactions.Color.teal(),
        )
        embed.add_field(name="Unix", value=f"`{int(utc_dt.timestamp())}`", inline=False)
        for label, formatted in variants:
            embed.add_field(name=label, value=formatted, inline=True)
        embed.add_field(
            name="UTC",
            value=f"{format_dt(utc_dt, style='F')} (Relative {format_dt(utc_dt, style='R')})",
            inline=False,
        )
        embed.set_footer(text="Salin format yang sesuai dan tempelkan langsung ke chat Discord.")
        await ctx.send(embed=embed, ephemeral=True)

    @interactions.slash_command(name='timezone', description='Konversi waktu antar beberapa zona sekaligus.')
    @interactions.slash_option(
        name="waktu",
        description="Waktu sumber (contoh: 2025-01-31 19:30)",
        opt_type=interactions.OptionType.STRING,
        required=True,
    )
    @interactions.slash_option(
        name="zona_asal",
        description="Zona waktu asal. Kosongkan untuk mengikuti pengaturan server atau Asia/Jakarta.",
        opt_type=interactions.OptionType.STRING,
        required=False,
    )
    @interactions.slash_option(
        name="zona_tujuan",
        description="Daftar zona tujuan dipisahkan koma (misal: UTC,Asia/Tokyo,America/New_York)",
        opt_type=interactions.OptionType.STRING,
        required=False,
    )
    async def timezone(
        self,
        ctx: interactions.SlashContext,
        waktu: str,
        zona_asal: str | None = None,
        zona_tujuan: str | None = None,
    ) -> None:
        default_tz_name = await self._get_default_timezone(ctx.guild)
        try:
            origin_tz = resolve_timezone(zona_asal, fallback=default_tz_name)
        except ValueError as exc:
            await ctx.send(str(exc), ephemeral=True)
            return

        try:
            origin_dt = parse_datetime_input(waktu, origin_tz)
        except ValueError as exc:
            await ctx.send(str(exc), ephemeral=True)
            return

        raw_targets = zona_tujuan or "UTC"
        target_names = [name.strip() for name in raw_targets.split(",") if name.strip()]
        if "UTC" not in {name.upper() for name in target_names}:
            target_names.append("UTC")

        results: list[tuple[str, datetime]] = []
        errors: list[str] = []
        seen: set[str] = set()
        for candidate in target_names:
            try:
                target_tz = resolve_timezone(candidate, fallback=None)
            except ValueError:
                errors.append(candidate)
                continue
            label = format_timezone_display(target_tz)
            if label in seen:
                continue
            seen.add(label)
            converted = origin_dt.astimezone(target_tz)
            results.append((label, converted))

        if not results:
            message = "Tidak ada zona tujuan valid yang diberikan."
            if errors:
                message += f" Zona tidak valid: {', '.join(errors)}."
            await ctx.send(message, ephemeral=True)
            return

        embed = interactions.Embed(
            title="Konversi Zona Waktu",
            description=(
                f"Sumber: {format_dt(origin_dt, style='F')}\n"
                f"Zona asal: {format_timezone_display(origin_tz)}"
            ),
            color=interactions.Color.dark_teal(),
        )
        for label, dt_value in results:
            embed.add_field(
                name=label,
                value=(
                    f"{format_dt(dt_value, style='F')}\n"
                    f"Relative: {format_dt(dt_value, style='R')}"
                ),
                inline=False,
            )
        if errors:
            truncated = self._limit_text(", ".join(errors), 200)
            embed.set_footer(text=f"Zona diabaikan: {truncated}")
        await ctx.send(embed=embed, ephemeral=True)

    @interactions.slash_command(name='carijadwalsholat', description='Cari ID kota (Indonesia) atau kode JAKIM (Malaysia) untuk jadwal sholat.')
    @interactions.slash_option(
        name="negara",
        description="Pilih negara sumber data",
        opt_type=interactions.OptionType.STRING,
        required=True,
        choices=[
            interactions.SlashCommandChoice(name="Indonesia", value="indonesia"),
            interactions.SlashCommandChoice(name="Malaysia", value="malaysia"),
        ],
    )
    @interactions.slash_option(
        name="keyword",
        description="Ketik nama kota/zona yang ingin dicari",
        opt_type=interactions.OptionType.STRING,
        required=True,
    )
    @interactions.slash_option(
        name="batas",
        description="Batas jumlah hasil (1-25)",
        opt_type=interactions.OptionType.INTEGER,
        min_value=1,
        max_value=25,
        required=False,
    )
    async def carijadwalsholat(
        self,
        ctx: interactions.SlashContext,
        negara: str,
        keyword: str,
        batas: int = 10,
    ) -> None:
        keyword = keyword.strip()
        if len(keyword) < 2:
            await ctx.send(
                "Masukkan minimal 2 karakter untuk melakukan pencarian.",
                ephemeral=True,
            )
            return

        batas = int(batas)

        try:
            if negara == "indonesia":
                results = await self._search_indonesia_locations(keyword)
                limited = results[:batas]
                embed = self._build_search_embed_indonesia(keyword, limited)
            else:
                results = await self._search_malaysia_zones(keyword)
                limited = results[:batas]
                embed = self._build_search_embed_malaysia(keyword, limited)
        except PrayerAPIError as exc:
            await ctx.send(str(exc), ephemeral=True)
            return

        if not limited:
            await ctx.send(
                "Tidak ada hasil yang cocok. Coba kata kunci lain.",
                ephemeral=True,
            )
            return

        await ctx.send(embed=embed, ephemeral=True)

    @interactions.slash_command(name='userinfo', description='Menampilkan info pengguna.')
    async def userinfo(self, ctx: interactions.SlashContext, user: interactions.User | None = None) -> None:
        user = user or ctx.author
        embed = interactions.Embed(title=f"Info {user.display_name}", color=interactions.Color.green())
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.add_field(name="ID", value=str(user.id))
        embed.add_field(name="Bot?", value="Ya" if user.bot else "Tidak")
        embed.add_field(name="Dibuat", value=format_dt(user.created_at, style="F"), inline=False)
        if isinstance(user, interactions.Member):
            embed.add_field(name="Bergabung", value=format_dt(user.joined_at, style="F"), inline=False)
            roles = ", ".join(role.mention for role in user.roles[1:]) or "Tidak ada"
            embed.add_field(name="Role", value=roles, inline=False)
        await ctx.send(embed=embed)

    @interactions.slash_command(name='roleinfo', description='Tampilkan detail lengkap sebuah role di server.')
    @interactions.slash_option(
        name="role",
        description="Role yang ingin dilihat informasinya",
        opt_type=interactions.OptionType.ROLE,
        required=True,
    )
    async def roleinfo(self, ctx: interactions.SlashContext, role: interactions.Role) -> None:
        if ctx.guild is None:
            await ctx.send("Perintah ini hanya dapat digunakan di dalam server.", ephemeral=True)
            return

        color = role.color if role.color.value else interactions.Color.light_gray()
        embed = interactions.Embed(
            title=f"Role: {role.name}",
            description=role.mention if not role.is_default() else "Role default (@everyone)",
            color=color,
        )
        embed.add_field(name="ID", value=str(role.id))
        embed.add_field(name="Posisi", value=str(role.position))
        embed.add_field(name="Dibuat", value=format_dt(role.created_at, style="F"), inline=False)
        color_hex = f"#{role.color.value:06X}" if role.color.value else "#000000"
        embed.add_field(name="Warna", value=color_hex, inline=True)
        embed.add_field(name="Dapat disebut", value="Ya" if role.mentionable else "Tidak", inline=True)
        embed.add_field(name="Terpisah", value="Ya" if role.hoist else "Tidak", inline=True)
        embed.add_field(name="Dikelola bot/integrasi", value="Ya" if role.managed else "Tidak", inline=True)

        members = list(role.members)
        total_members = len(members)
        bot_members = sum(1 for member in members if getattr(member, "bot", False))
        human_members = total_members - bot_members
        embed.add_field(
            name="Jumlah anggota",
            value=f"Total: {total_members}\nManusia: {human_members}\nBot: {bot_members}",
            inline=False,
        )

        highlight = self._highlight_permissions(role)
        embed.add_field(name="Izin penting", value=highlight, inline=False)

        enabled_permissions = [
            perm.replace("_", " ").title()
            for perm, allowed in role.permissions
            if allowed
        ]
        embed.add_field(name="Jumlah izin aktif", value=str(len(enabled_permissions)), inline=True)
        if enabled_permissions:
            preview = self._limit_text(", ".join(enabled_permissions[:15]), 512)
            embed.add_field(name="Contoh izin aktif", value=preview or "-", inline=False)

        embed.set_footer(text=f"ID: {role.id}")
        await ctx.send(embed=embed, ephemeral=True)

    @interactions.slash_command(name='serverinfo', description='Menampilkan info server.')
    async def serverinfo(self, ctx: interactions.SlashContext) -> None:
        guild = ctx.guild
        if guild is None:
            await ctx.send("Perintah ini hanya dapat digunakan dalam server.", ephemeral=True)
            return
        stats = gather_guild_statistics(guild)
        embed = interactions.Embed(title=guild.name, color=interactions.Color.gold())
        if guild.description:
            embed.description = self._limit_text(guild.description, 350)
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        if guild.banner:
            embed.set_image(url=guild.banner.url)
        elif guild.splash:
            embed.set_image(url=guild.splash.url)

        embed.add_field(name="ID", value=str(guild.id), inline=True)
        embed.add_field(name="Owner", value=guild.owner.mention if guild.owner else "Tidak diketahui", inline=True)
        embed.add_field(name="Dibuat", value=format_dt(guild.created_at, style="F"), inline=False)

        embed.add_field(
            name="Anggota",
            value=(
                f"Total: {stats.total_members}\n"
                f"Manusia: {stats.human_members}\n"
                f"Bot: {stats.bot_members}"
            ),
            inline=True,
        )
        embed.add_field(
            name="Channel",
            value=(
                f"Teks: {stats.text_channels}\n"
                f"Suara: {stats.voice_channels}\n"
                f"Stage: {stats.stage_channels}\n"
                f"Forum: {stats.forum_channels}\n"
                f"Kategori: {stats.categories}\n"
                f"Thread aktif: {stats.thread_channels}"
            ),
            inline=True,
        )
        embed.add_field(
            name="Boost",
            value=(
                f"Tingkat: {stats.boost_level}\n"
                f"Jumlah: {stats.boosts}"
            ),
            inline=True,
        )

        embed.add_field(
            name="Koleksi",
            value=(
                f"Role: {stats.roles}\n"
                f"Emoji: {stats.emoji_count}\n"
                f"Stiker: {stats.sticker_count}"
            ),
            inline=True,
        )
        embed.add_field(name="Acara Terjadwal", value=str(stats.scheduled_events), inline=True)
        embed.add_field(name="Locale", value=guild.preferred_locale or "-", inline=True)

        def _format_enum(value: Any) -> str:
            raw = getattr(value, "name", value)
            if isinstance(raw, str):
                return raw.replace("_", " ").title()
            return str(raw)

        embed.add_field(
            name="Keamanan",
            value=(
                f"Verifikasi: {_format_enum(guild.verification_level)}\n"
                f"Filter Konten: {_format_enum(guild.explicit_content_filter)}\n"
                f"NSFW: {_format_enum(getattr(guild, 'nsfw_level', 'unknown'))}"
            ),
            inline=False,
        )

        features = getattr(guild, "features", [])
        if features:
            formatted_features = ", ".join(sorted(feature.replace("_", " ").title() for feature in features))
            embed.add_field(name="Fitur Server", value=self._limit_text(formatted_features, 1024), inline=False)

        embed.set_footer(text=f"ID: {guild.id}")
        await ctx.send(embed=embed)

    @interactions.slash_command(name='channelinfo', description='Diagnostik lengkap sebuah channel. Kosongkan untuk channel saat ini.')
    @interactions.slash_option(
        name="channel",
        description="Channel yang ingin dianalisis. Kosongkan untuk menggunakan channel saat ini.",
        opt_type=interactions.OptionType.CHANNEL,
        required=False,
    )
    async def channelinfo(
        self,
        ctx: interactions.SlashContext,
        channel: interactions.GuildChannel | None = None,
    ) -> None:
        if ctx.guild is None:
            await ctx.send("Perintah ini hanya dapat digunakan dalam server.", ephemeral=True)
            return

        target = channel or ctx.channel
        if not isinstance(target, interactions.GuildChannel):
            await ctx.send("Tidak dapat membaca informasi channel ini.", ephemeral=True)
            return

        if isinstance(target, interactions.GuildVoice):
            color = interactions.Color.orange()
        elif isinstance(target, interactions.GuildStageVoice):
            color = interactions.Color.dark_magenta()
        elif isinstance(target, interactions.GuildCategory):
            color = interactions.Color.dark_gray()
        elif isinstance(target, interactions.ThreadChannel):
            color = interactions.Color.gold()
        else:
            color = interactions.Color.blurple()

        title = getattr(target, "name", str(target.id))
        embed = interactions.Embed(title=f"Channel #{title}", color=color)
        mention = getattr(target, "mention", None)
        if mention:
            embed.description = mention

        embed.add_field(name="ID", value=str(target.id), inline=True)
        channel_type = getattr(target, "type", None)
        type_label = channel_type.name.replace("_", " ").title() if channel_type else target.__class__.__name__
        embed.add_field(name="Jenis", value=type_label, inline=True)

        category = getattr(target, "category", None)
        if category:
            embed.add_field(name="Kategori", value=getattr(category, "mention", category.name), inline=True)

        parent = getattr(target, "parent", None)
        if parent:
            embed.add_field(name="Parent", value=getattr(parent, "mention", getattr(parent, "name", "-")), inline=True)

        created_at = getattr(target, "created_at", None)
        if isinstance(created_at, datetime):
            embed.add_field(name="Dibuat", value=format_dt(created_at, style="F"), inline=False)

        position = getattr(target, "position", None)
        if isinstance(position, int):
            embed.add_field(name="Posisi", value=str(position), inline=True)

        nsfw_flag = getattr(target, "nsfw", None)
        if nsfw_flag is not None:
            embed.add_field(name="NSFW", value="Ya" if nsfw_flag else "Tidak", inline=True)

        if isinstance(target, interactions.GuildText):
            slowmode = target.slowmode_delay or 0
            embed.add_field(name="Slowmode", value=f"{slowmode} detik" if slowmode else "Tidak aktif", inline=True)
            topic = self._limit_text(target.topic, 512) or "Tidak ada"
            embed.add_field(name="Topik", value=topic, inline=False)
        elif isinstance(target, interactions.GuildForum):
            slowmode = target.default_thread_slowmode_delay or 0
            embed.add_field(name="Slowmode thread", value=f"{slowmode} detik" if slowmode else "Tidak aktif", inline=True)
            auto_archive = target.default_auto_archive_duration or 0
            embed.add_field(name="Auto archive", value=f"{auto_archive} menit", inline=True)
            tags = target.available_tags
            if tags:
                tag_preview = ", ".join(tag.name for tag in tags[:10])
                embed.add_field(name="Tag tersedia", value=self._limit_text(tag_preview, 512), inline=False)
        elif isinstance(target, interactions.GuildVoice):
            embed.add_field(name="Bitrate", value=f"{target.bitrate // 1000} kbps", inline=True)
            embed.add_field(name="Batas pengguna", value=str(target.user_limit) if target.user_limit else "Tidak ada", inline=True)
            embed.add_field(name="Region RTC", value=target.rtc_region or "Otomatis", inline=True)
        elif isinstance(target, interactions.GuildStageVoice):
            embed.add_field(name="Bitrate", value=f"{target.bitrate // 1000} kbps", inline=True)
            embed.add_field(name="Batas pembicara", value=str(target.user_limit) if target.user_limit else "Tidak ada", inline=True)
            if target.topic:
                embed.add_field(name="Topik", value=self._limit_text(target.topic, 512), inline=False)
        elif isinstance(target, interactions.GuildCategory):
            child_count = len(target.channels)
            embed.add_field(name="Jumlah channel", value=str(child_count), inline=True)
        elif isinstance(target, interactions.ThreadChannel):
            owner = getattr(target, "owner", None)
            if owner:
                owner_value = owner.mention
            elif getattr(target, "owner_id", None):
                owner_value = f"<@{target.owner_id}>"
            else:
                owner_value = "Tidak diketahui"
            embed.add_field(name="Owner", value=owner_value, inline=True)
            embed.add_field(name="Auto archive", value=f"{target.auto_archive_duration} menit", inline=True)
            embed.add_field(name="Terkunci", value="Ya" if target.locked else "Tidak", inline=True)
            embed.add_field(name="Terarsip", value="Ya" if target.archived else "Tidak", inline=True)
            embed.add_field(name="Jumlah pesan", value=str(target.message_count or 0), inline=True)
            embed.add_field(name="Jumlah anggota", value=str(target.member_count or 0), inline=True)
            slowmode = getattr(target, "slowmode_delay", 0) or 0
            if slowmode:
                embed.add_field(name="Slowmode", value=f"{slowmode} detik", inline=True)

        embed.set_footer(text=f"ID: {target.id}")
        await ctx.send(embed=embed, ephemeral=True)

    @interactions.slash_command(name='botstats', description='Statistik bot singkat.')
    async def botstats(self, ctx: interactions.SlashContext) -> None:
        uptime_seconds = int(time.time() - self.launch_time)
        days, remainder = divmod(uptime_seconds, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, _ = divmod(remainder, 60)
        uptime_text = f"{days} hari {hours} jam {minutes} menit"
        started_at = datetime.fromtimestamp(self.launch_time, tz=dt_timezone.utc)

        scheduler_jobs = 0
        job_list: list[str] = []
        if self.bot.scheduler:
            scheduler_jobs = self.bot.scheduler.job_count()
            job_list = self.bot.scheduler.list_jobs()

        resource_stats = process_resource_snapshot()
        command_count = len(self.bot.tree.get_commands())
        shard_count = getattr(self.bot, "shard_count", None) or 1
        cog_count = len(self.bot.cogs)

        embed = interactions.Embed(title="Statistik Bot", color=interactions.Color.purple())
        embed.add_field(name="Versi Python", value=platform.python_version(), inline=True)
        embed.add_field(name="discord.py", value=discord.__version__, inline=True)
        embed.add_field(name="Shard", value=str(shard_count), inline=True)
        embed.add_field(name="Guild", value=str(len(self.bot.guilds)), inline=True)
        embed.add_field(name="Pengguna unik", value=str(len(self.bot.users)), inline=True)
        embed.add_field(name="Total cog", value=str(cog_count), inline=True)
        embed.add_field(name="Perintah terdaftar", value=str(command_count), inline=True)
        embed.add_field(name="Tugas terjadwal", value=str(scheduler_jobs), inline=True)
        embed.add_field(name="Uptime", value=f"{uptime_text} (Sejak {format_dt(started_at, style='R')})", inline=False)

        memory_mb = resource_stats.get("memory_mb")
        if memory_mb is not None:
            embed.add_field(name="Memori proses", value=f"{memory_mb:.1f} MB", inline=True)

        load_average = resource_stats.get("load_average")
        if isinstance(load_average, tuple) and any(value is not None for value in load_average):
            formatted = " / ".join(
                f"{value:.2f}" if isinstance(value, (int, float)) else "-"
                for value in load_average
            )
            embed.add_field(name="Load Average (1m/5m/15m)", value=formatted, inline=True)

        if job_list:
            preview = ", ".join(job_list[:5])
            embed.add_field(name="ID job aktif", value=self._limit_text(preview, 200), inline=False)

        embed.set_footer(text="Gunakan /help untuk melihat seluruh kemampuan bot.")
        await ctx.send(embed=embed, ephemeral=True)

    @interactions.slash_command(name='jadwalsholat', description='Menampilkan jadwal sholat harian berdasarkan negara.')
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
        ctx: interactions.SlashContext,
        negara: app_commands.Choice[str],
        lokasi: str,
        tahun: int | None = None,
        bulan: int | None = None,
        tanggal: int | None = None,
    ) -> None:
        try:
            target_date = self._build_target_date(negara.value, tahun, bulan, tanggal)
        except PrayerAPIError as exc:
            await ctx.send(str(exc), ephemeral=True)
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
                await ctx.send(str(exc), ephemeral=True)
            else:
                await ctx.send(str(exc), ephemeral=True)
            return
        except Exception:  # noqa: BLE001
            logger = getattr(self.bot, "log", None)
            if logger:
                logger.exception("Gagal mengambil jadwal sholat")
            message = "Terjadi kesalahan saat mengambil jadwal sholat. Coba lagi nanti."
            if interaction.response.is_done():
                await ctx.send(message, ephemeral=True)
            else:
                await ctx.send(message, ephemeral=True)
            return

        if interaction.response.is_done():
            await ctx.send(embed=embed)
        else:
            await ctx.send(embed=embed)

    @jadwalsholat.autocomplete("lokasi")
    async def jadwalsholat_lokasi_autocomplete(
        self,
        ctx: interactions.SlashContext,
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

    def _build_search_embed_indonesia(self, keyword: str, results: list[dict[str, Any]]) -> interactions.Embed:
        embed = interactions.Embed(
            title="Pencarian Kota Jadwal Sholat (Indonesia)",
            description=f"Kata kunci: `{keyword}`",
            color=interactions.Color.blue(),
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

    def _build_search_embed_malaysia(self, keyword: str, results: list[dict[str, Any]]) -> interactions.Embed:
        embed = interactions.Embed(
            title="Pencarian Zona JAKIM (Malaysia)",
            description=f"Kata kunci: `{keyword}`",
            color=interactions.Color.dark_teal(),
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
    ) -> interactions.Embed:
        lokasi = month_payload.get("lokasi", kota_id)
        daerah = month_payload.get("daerah")
        judul = f"Jadwal Sholat • {lokasi.title() if isinstance(lokasi, str) else lokasi}"
        deskripsi = day_payload.get("tanggal") or day_payload.get("date") or ""
        if daerah:
            deskripsi += f"\n{daerah.title() if isinstance(daerah, str) else daerah}"

        embed = interactions.Embed(title=judul, description=deskripsi.strip(), color=interactions.Color.teal())
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
    ) -> interactions.Embed:
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
        embed = interactions.Embed(title=judul, description=deskripsi, color=interactions.Color.green())

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


def setup(bot: ForUS) -> None:
    Utility(bot)
