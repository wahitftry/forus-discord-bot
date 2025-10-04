from __future__ import annotations

import random
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Optional

import discord
from discord import app_commands
from discord.ext import commands

if TYPE_CHECKING:
    from bot.main import ForUS

LOVE_COOLDOWN = timedelta(hours=20)
LOVE_SYNC_WINDOW = timedelta(hours=6)
LOVE_SYNC_BONUS = 12


def _now() -> datetime:
    return datetime.now(UTC)


def _format_timedelta(delta: timedelta) -> str:
    total_seconds = int(delta.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    parts: list[str] = []
    if hours:
        parts.append(f"{hours} jam")
    if minutes:
        parts.append(f"{minutes} menit")
    if not parts:
        parts.append(f"{seconds} detik")
    return " ".join(parts)


def _format_duration_since(start: datetime, now: datetime) -> str:
    delta = now - start
    days = delta.days
    years, remaining_days = divmod(days, 365)
    months, days = divmod(remaining_days, 30)
    parts: list[str] = []
    if years:
        parts.append(f"{years} tahun")
    if months:
        parts.append(f"{months} bulan")
    if days:
        parts.append(f"{days} hari")
    if not parts:
        parts.append("baru saja")
    return ", ".join(parts)


class Couples(commands.GroupCog, name="couple"):
    def __init__(self, bot: ForUS) -> None:
        super().__init__()
        self.bot = bot

    async def _get_repo(self, interaction: discord.Interaction) -> Optional[tuple[int, ForUS]]:
        if interaction.guild is None:
            await interaction.response.send_message("Perintah ini hanya bisa dipakai di dalam server.", ephemeral=True)
            return None
        if self.bot.couple_repo is None:
            await interaction.response.send_message("Repositori pasangan belum siap. Coba lagi nanti.", ephemeral=True)
            return None
        return interaction.guild.id, self.bot

    async def _resolve_member(self, guild: discord.Guild, user_id: int) -> Optional[discord.Member]:
        member = guild.get_member(user_id)
        if member is None:
            try:
                member = await guild.fetch_member(user_id)
            except discord.HTTPException:
                return None
        return member

    @app_commands.command(name="propose", description="Ajukan pasangan kepada seseorang spesial.")
    @app_commands.describe(pasangan="Pengguna yang ingin diajak menjadi pasangan", pesan="Pesan manis opsional")
    async def propose(self, interaction: discord.Interaction, pasangan: discord.User, pesan: Optional[str] = None) -> None:
        repo_info = await self._get_repo(interaction)
        if repo_info is None:
            return
        guild_id, bot = repo_info
        repo = bot.couple_repo
        assert interaction.guild is not None
        assert repo is not None

        if pasangan.bot:
            await interaction.response.send_message("Kamu tidak bisa berpasangan dengan bot.", ephemeral=True)
            return
        if pasangan.id == interaction.user.id:
            await interaction.response.send_message("Cinta diri itu penting, tapi pilihlah pasangan lain.", ephemeral=True)
            return
        if pesan and len(pesan) > 240:
            await interaction.response.send_message("Pesan terlalu panjang (maksimal 240 karakter).", ephemeral=True)
            return

        # Cek apakah kedua pihak masih kosong
        if await repo.user_has_active_or_pending(guild_id, interaction.user.id):
            await interaction.response.send_message("Kamu sudah memiliki pasangan atau lamaran yang belum selesai.", ephemeral=True)
            return
        if await repo.user_has_active_or_pending(guild_id, pasangan.id):
            await interaction.response.send_message(f"{pasangan.mention} sudah memiliki pasangan atau lamaran lain.", ephemeral=True)
            return

        existing = await repo.get_pair(guild_id, interaction.user.id, pasangan.id)
        if existing and existing.status == "pending":
            await interaction.response.send_message("Lamaranmu sebelumnya masih menunggu jawaban.", ephemeral=True)
            return
        if existing and existing.status == "active":
            await interaction.response.send_message("Kalian sudah resmi menjadi pasangan!", ephemeral=True)
            return

        record = await repo.create_proposal(guild_id, interaction.user.id, pasangan.id, pesan)
        embed = discord.Embed(
            title="💝 Lamaran Baru!",
            description=f"{interaction.user.mention} mengajak {pasangan.mention} menjadi pasangan!",
            color=discord.Color.magenta(),
        )
        if pesan:
            embed.add_field(name="Pesan", value=pesan, inline=False)
        embed.set_footer(text="Gunakan /couple respond untuk menjawab lamaran.")

        await interaction.response.send_message(
            embed=embed,
            allowed_mentions=discord.AllowedMentions(users=[interaction.user, pasangan]),
        )

        try:
            await pasangan.send(
                f"{interaction.user.display_name} mengajakmu jadi pasangan di server {interaction.guild.name}! Gunakan /couple respond di server untuk menjawab."
            )
        except discord.Forbidden:
            pass

    @app_commands.choices(keputusan=[
        app_commands.Choice(name="Terima", value="accept"),
        app_commands.Choice(name="Tolak", value="reject"),
    ])
    @app_commands.describe(keputusan="Jawabanmu atas lamaran", pesan="Pesan opsional untuk pasangan")
    @app_commands.command(name="respond", description="Jawab lamaran pasangan yang masuk.")
    async def respond(self, interaction: discord.Interaction, keputusan: app_commands.Choice[str], pesan: Optional[str] = None) -> None:
        repo_info = await self._get_repo(interaction)
        if repo_info is None:
            return
        guild_id, bot = repo_info
        repo = bot.couple_repo
        assert interaction.guild is not None
        assert repo is not None

        if pesan and len(pesan) > 240:
            await interaction.response.send_message("Pesan terlalu panjang (maksimal 240 karakter).", ephemeral=True)
            return

        pending = await repo.get_pending_for_target(guild_id, interaction.user.id)
        if pending is None:
            await interaction.response.send_message("Tidak ada lamaran yang perlu kamu jawab saat ini.", ephemeral=True)
            return

        initiator_id = pending.partner_id(interaction.user.id)
        initiator = await self._resolve_member(interaction.guild, initiator_id) if initiator_id else None

        if keputusan.value == "accept":
            updated = await repo.accept_proposal(pending.id)
            if updated is None or updated.status != "active":
                await interaction.response.send_message("Lamaran sudah tidak berlaku.", ephemeral=True)
                return
            now = _now()
            anniversary = updated.anniversary
            ann_display = "hari ini" if not anniversary else anniversary
            embed = discord.Embed(
                title="💞 Selamat!",
                description=f"{interaction.user.mention} menerima lamaran {initiator.mention if initiator else '<pasangan>'}!",
                color=discord.Color.magenta(),
            )
            embed.add_field(name="Tanggal Anniversary", value=ann_display, inline=True)
            embed.add_field(name="Love Points", value=str(updated.love_points), inline=True)
            embed.set_footer(text="Kirim /couple affection setiap hari untuk menambah love points!")
            await interaction.response.send_message(
                embed=embed,
                allowed_mentions=discord.AllowedMentions(users=[interaction.user] + ([initiator] if initiator else [])),
            )
            if initiator:
                dm_message = f"{interaction.user.display_name} menerima lamaranmu!"
                if pesan:
                    dm_message += f" Pesannya: {pesan}"
                try:
                    await initiator.send(dm_message)
                except discord.Forbidden:
                    pass
        else:
            updated = await repo.reject_proposal(pending.id, interaction.user.id)
            await interaction.response.send_message("Lamaran telah ditolak. Semoga kamu nyaman dengan keputusanmu.", ephemeral=True)
            if initiator:
                message = f"{interaction.user.display_name} menolak lamarannya."
                if pesan:
                    message += f" Pesannya: {pesan}"
                try:
                    await initiator.send(message)
                except discord.Forbidden:
                    pass

    @app_commands.describe(target="Cek status pasangan untuk pengguna tertentu (opsional)")
    @app_commands.command(name="status", description="Lihat status hubunganmu atau orang lain.")
    async def status(self, interaction: discord.Interaction, target: Optional[discord.User] = None) -> None:
        repo_info = await self._get_repo(interaction)
        if repo_info is None:
            return
        guild_id, bot = repo_info
        repo = bot.couple_repo
        assert interaction.guild is not None
        assert repo is not None

        user = target or interaction.user
        record = await repo.get_relationship(guild_id, user.id, statuses=("pending", "active"))
        if record is None:
            await interaction.response.send_message("Belum ada data pasangan untuk pengguna tersebut.", ephemeral=True)
            return

        now = _now()
        partner_id = record.partner_id(user.id)
        partner = await self._resolve_member(interaction.guild, partner_id) if partner_id else None
        embed = discord.Embed(title="Status Pasangan", color=discord.Color.blurple())
        embed.add_field(name="Pengguna", value=f"{user.mention}", inline=True)
        embed.add_field(name="Pasangan", value=partner.mention if partner else f"<@{partner_id}>", inline=True)
        embed.add_field(name="Status", value=record.status.capitalize(), inline=True)

        if record.anniversary:
            try:
                ann_date = datetime.fromisoformat(record.anniversary)
                embed.add_field(name="Tanggal Anniversary", value=record.anniversary, inline=True)
                embed.add_field(name="Lama Bersama", value=_format_duration_since(ann_date, now), inline=True)
            except ValueError:
                embed.add_field(name="Tanggal Anniversary", value=record.anniversary, inline=True)
        if record.love_points:
            embed.add_field(name="Love Points", value=str(record.love_points), inline=True)

        last_user = record.last_affection_for(user.id)
        partner_last = record.last_affection_for(partner_id or 0) if partner_id else None
        if last_user:
            try:
                last_dt = datetime.fromisoformat(last_user)
                embed.add_field(name="Afirmasi Terakhir", value=_format_timedelta(now - last_dt), inline=True)
            except ValueError:
                pass
        if partner_last:
            try:
                partner_dt = datetime.fromisoformat(partner_last)
                embed.add_field(name="Afirmasi dari Pasangan", value=_format_timedelta(now - partner_dt), inline=True)
            except ValueError:
                pass

        await interaction.response.send_message(embed=embed, ephemeral=True)

    anniversary = app_commands.Group(name="anniversary", description="Kelola tanggal anniversary pasangan")

    @anniversary.command(name="set", description="Atur tanggal anniversary (format YYYY-MM-DD)")
    async def anniversary_set(self, interaction: discord.Interaction, tanggal: str) -> None:
        repo_info = await self._get_repo(interaction)
        if repo_info is None:
            return
        guild_id, bot = repo_info
        repo = bot.couple_repo
        assert interaction.guild is not None
        assert repo is not None

        record = await repo.get_relationship(guild_id, interaction.user.id, statuses=("active",))
        if record is None:
            await interaction.response.send_message("Kamu belum memiliki pasangan aktif untuk mengatur anniversary.", ephemeral=True)
            return

        try:
            parsed = datetime.fromisoformat(tanggal)
        except ValueError:
            await interaction.response.send_message("Format tanggal tidak valid. Gunakan YYYY-MM-DD.", ephemeral=True)
            return

        updated = await repo.update_anniversary(record.id, parsed.date().isoformat())
        if updated is None:
            await interaction.response.send_message("Gagal memperbarui tanggal anniversary.", ephemeral=True)
            return

        await interaction.response.send_message(
            f"Tanggal anniversary diperbarui menjadi {parsed.date().isoformat()}.",
            ephemeral=True,
        )

    @app_commands.command(name="affection", description="Tambahkan love points harian bersama pasangan.")
    async def affection(self, interaction: discord.Interaction) -> None:
        repo_info = await self._get_repo(interaction)
        if repo_info is None:
            return
        guild_id, bot = repo_info
        repo = bot.couple_repo
        assert interaction.guild is not None
        assert repo is not None

        record = await repo.get_relationship(guild_id, interaction.user.id, statuses=("active",))
        if record is None:
            await interaction.response.send_message("Kamu belum memiliki pasangan aktif.", ephemeral=True)
            return

        now = _now()
        last_str = record.last_affection_for(interaction.user.id)
        if last_str:
            try:
                last_dt = datetime.fromisoformat(last_str)
            except ValueError:
                last_dt = None
            if last_dt and now - last_dt < LOVE_COOLDOWN:
                remaining = LOVE_COOLDOWN - (now - last_dt)
                await interaction.response.send_message(
                    f"Kamu bisa mengirim love point lagi dalam {_format_timedelta(remaining)}.",
                    ephemeral=True,
                )
                return

        partner_id = record.partner_id(interaction.user.id)
        partner_last = record.last_affection_for(partner_id or 0) if partner_id else None
        base_points = random.randint(15, 35)
        bonus = 0
        if partner_last:
            try:
                partner_dt = datetime.fromisoformat(partner_last)
                if abs((now - partner_dt).total_seconds()) <= LOVE_SYNC_WINDOW.total_seconds():
                    bonus = LOVE_SYNC_BONUS
            except ValueError:
                bonus = 0

        total = base_points + bonus
        updated = await repo.add_love_points(record.id, total)
        if updated is None:
            await interaction.response.send_message("Gagal memperbarui love points.", ephemeral=True)
            return
        await repo.update_last_affection(updated, interaction.user.id, now.isoformat())

        if bonus:
            bonus_text = f" (bonus {bonus})"
        else:
            bonus_text = ""
        description = f"Love points bertambah **{total}**{bonus_text}. Total sekarang **{updated.love_points}**."
        if partner_last and bonus:
            description += " Kamu mendapat bonus karena kompak dengan pasangan!"
        await interaction.response.send_message(description, ephemeral=True)

    @app_commands.command(name="leaderboard", description="Lihat pasangan paling romantis di server.")
    async def leaderboard(self, interaction: discord.Interaction) -> None:
        repo_info = await self._get_repo(interaction)
        if repo_info is None:
            return
        guild_id, bot = repo_info
        repo = bot.couple_repo
        assert interaction.guild is not None
        assert repo is not None

        records = await repo.list_leaderboard(guild_id, limit=10)
        if not records:
            await interaction.response.send_message("Belum ada pasangan aktif di server ini.")
            return

        lines: list[str] = []
        for idx, record in enumerate(records, start=1):
            one = await self._resolve_member(interaction.guild, record.member_one_id)
            two = await self._resolve_member(interaction.guild, record.member_two_id)
            name_one = one.mention if one else f"<@{record.member_one_id}>"
            name_two = two.mention if two else f"<@{record.member_two_id}>"
            crown = "👑 " if idx == 1 else ""
            lines.append(f"{crown}**{idx}.** {name_one} ❤️ {name_two} — {record.love_points} LP")

        embed = discord.Embed(title="Papan Cinta Server", description="\n".join(lines), color=discord.Color.red())
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="breakup", description="Akhiri hubungan dengan pasangan saat ini.")
    @app_commands.describe(alasan="Alasan opsional untuk pasanganmu")
    async def breakup(self, interaction: discord.Interaction, alasan: Optional[str] = None) -> None:
        repo_info = await self._get_repo(interaction)
        if repo_info is None:
            return
        guild_id, bot = repo_info
        repo = bot.couple_repo
        assert interaction.guild is not None
        assert repo is not None

        if alasan and len(alasan) > 240:
            await interaction.response.send_message("Alasan terlalu panjang (maksimal 240 karakter).", ephemeral=True)
            return

        record = await repo.get_relationship(guild_id, interaction.user.id, statuses=("active",))
        if record is None:
            await interaction.response.send_message("Tidak ada hubungan aktif yang bisa diakhiri.", ephemeral=True)
            return

        updated = await repo.end_relationship(record.id, interaction.user.id)
        if updated is None:
            await interaction.response.send_message("Terjadi kesalahan saat mengakhiri hubungan.", ephemeral=True)
            return

        partner_id = record.partner_id(interaction.user.id)
        partner = await self._resolve_member(interaction.guild, partner_id) if partner_id else None
        await interaction.response.send_message("Hubungan telah diakhiri. Semoga keputusanmu membawa kebaikan.", ephemeral=True)

        if partner:
            reason = f" Pesan darinya: {alasan}" if alasan else ""
            try:
                await partner.send(
                    f"{interaction.user.display_name} mengakhiri hubungan kalian di server {interaction.guild.name}.{reason}"
                )
            except discord.Forbidden:
                pass


async def setup(bot: ForUS) -> None:
    await bot.add_cog(Couples(bot))
