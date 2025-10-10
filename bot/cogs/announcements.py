from __future__ import annotations

from datetime import datetime, time, timezone
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

import interactions

if TYPE_CHECKING:
    from bot.main import ForUS

DEFAULT_TZ = ZoneInfo("Asia/Jakarta")


# Permissions moved to command decorators
class Announcements(interactions.Extension):
    # MANUAL REVIEW: GroupCog -> Extension with slash_command group
    def __init__(self, bot: ForUS) -> None:
        super().__init__()
        self.bot = bot

    async def cog_load(self) -> None:
        if self.bot.announcement_repo is None:
            return
        pending = await self.bot.announcement_repo.list_pending_all()
        for announcement in pending:
            run_time = datetime.fromisoformat(announcement.scheduled_at)
            self._schedule_announcement(announcement.id, run_time)

    def _schedule_announcement(self, announcement_id: int, run_time: datetime) -> None:
        if not self.bot.scheduler:
            return
        self.bot.scheduler.schedule_once(
            f"announcement-{announcement_id}",
            run_time,
            self._fire_announcement,
            announcement_id,
        )

    async def _ensure_repos(self, ctx: interactions.SlashContext) -> bool:
        if not ctx.guild:
            await ctx.send("Perintah ini hanya dapat digunakan di server.", ephemeral=True)
            return False
        if self.bot.announcement_repo is None or self.bot.guild_repo is None:
            await ctx.send("Repositori pengumuman belum siap.", ephemeral=True)
            return False
        return True

    async def _fire_announcement(self, announcement_id: int) -> None:
        if self.bot.announcement_repo is None:
            return
        announcement = await self.bot.announcement_repo.get(announcement_id)
        if announcement is None or announcement.status != "pending":
            return
        guild = self.bot.get_guild(announcement.guild_id)
        if guild is None:
            await self.bot.announcement_repo.cancel(announcement_id)
            return
        channel = guild.get_channel(announcement.channel_id)
        if not isinstance(channel, interactions.GuildText):
            await self.bot.announcement_repo.cancel(announcement_id)
            return
        content_parts: list[str] = []
        if announcement.mention_role_id:
            content_parts.append(f"<@&{announcement.mention_role_id}>")
        if announcement.content:
            content_parts.append(announcement.content)
        content = "\n\n".join(content_parts) if content_parts else None
        embed = None
        if announcement.embed_title or announcement.embed_description or announcement.image_url:
            embed = interactions.Embed(
                title=announcement.embed_title or None,
                description=announcement.embed_description or None,
                color=interactions.Color.brand_green(),
            )
            if announcement.image_url:
                embed.set_image(url=announcement.image_url)
        if announcement.mention_role_id:
            allowed_mentions = discord.AllowedMentions(roles=[discord.Object(id=announcement.mention_role_id)], users=False, everyone=False)
        else:
            allowed_mentions = discord.AllowedMentions.none()
        try:
            await channel.send(content=content, embed=embed, allowed_mentions=allowed_mentions)
            await self.bot.announcement_repo.mark_sent(announcement_id)
            if self.bot.audit_repo is not None:
                await self.bot.audit_repo.add_entry(
                    guild.id,
                    action="announcement.sent",
                    actor_id=announcement.author_id,
                    target_id=announcement.channel_id,
                    context=str(announcement.id),
                )
        except discord.Forbidden:
            await self.bot.announcement_repo.cancel(announcement_id)

    @interactions.slash_command(name='schedule', description='Jadwalkan pengumuman otomatis.')
    @app_commands.describe(
        channel="Channel tujuan",
        tanggal="Tanggal (YYYY-MM-DD)",
        jam="Jam (HH:MM 24 jam)",
        zona_waktu="Zona waktu (misal Asia/Jakarta)",
        judul="Judul embed opsional",
        pesan="Isi pesan tambahan yang dikirim sebagai teks",
        deskripsi_embed="Isi embed opsional",
        mention_role="Role yang akan disebut",
        image_url="URL gambar opsional",
    )
    async def schedule(
        self,
        ctx: interactions.SlashContext,
        channel: interactions.GuildText,
        tanggal: str,
        jam: str,
        zona_waktu: str | None = None,
    judul: str | None = None,
    pesan: str | None = None,
    deskripsi_embed: str | None = None,
        mention_role: discord.Role | None = None,
        image_url: str | None = None,
    ) -> None:
        if not await self._ensure_repos(interaction):
            return
        assert ctx.guild is not None
        try:
            tanggal_obj = datetime.strptime(tanggal, "%Y-%m-%d").date()
            jam_obj = datetime.strptime(jam, "%H:%M").time()
        except ValueError:
            await ctx.send("Format tanggal atau jam tidak valid.", ephemeral=True)
            return
        tz_name = zona_waktu
        if not tz_name:
            settings = await self.bot.guild_repo.get(ctx.guild.id)
            tz_name = settings.timezone if settings else DEFAULT_TZ.key
        try:
            tzinfo = ZoneInfo(tz_name)
        except Exception:  # noqa: BLE001
            await ctx.send("Zona waktu tidak dikenali.", ephemeral=True)
            return
        local_dt = datetime.combine(tanggal_obj, jam_obj, tzinfo)
        utc_dt = local_dt.astimezone(timezone.utc)
        if utc_dt <= datetime.now(timezone.utc):
            await ctx.send("Waktu jadwal harus di masa depan.", ephemeral=True)
            return
        repo = self.bot.announcement_repo
        assert repo is not None
        announcement = await repo.create(
            ctx.guild.id,
            channel.id,
            ctx.author.id,
            content=pesan,
            embed_title=judul,
            embed_description=deskripsi_embed,
            mention_role_id=mention_role.id if mention_role else None,
            image_url=image_url,
            scheduled_at=utc_dt.isoformat(),
        )
        self._schedule_announcement(announcement.id, utc_dt)
        if self.bot.audit_repo is not None:
            await self.bot.audit_repo.add_entry(
                ctx.guild.id,
                action="announcement.schedule",
                actor_id=ctx.author.id,
                target_id=channel.id,
                context=str(announcement.id),
            )
        await ctx.send(
            f"Pengumuman dijadwalkan untuk {discord.utils.format_dt(utc_dt, style='F')} (UTC). ID: {announcement.id}",
            ephemeral=True,
        )

    @interactions.slash_command(name='list', description='Daftar pengumuman yang belum terkirim.')
    async def list_pending(self, ctx: interactions.SlashContext) -> None:
        if not await self._ensure_repos(interaction):
            return
        assert ctx.guild is not None
        repo = self.bot.announcement_repo
        assert repo is not None
        scheduled = await repo.list_pending(ctx.guild.id)
        if not scheduled:
            await ctx.send("Tidak ada pengumuman tertunda.", ephemeral=True)
            return
        embed = interactions.Embed(title="Pengumuman Tertunda", color=interactions.Color.purple())
        for item in scheduled[:15]:
            waktu = datetime.fromisoformat(item.scheduled_at).astimezone(timezone.utc)
            embed.add_field(
                name=f"ID {item.id} — <#{item.channel_id}>",
                value=f"Dijadwalkan: {discord.utils.format_dt(waktu, style='F')}\nStatus: {item.status}",
                inline=False,
            )
        await ctx.send(embed=embed, ephemeral=True)

    @interactions.slash_command(name='cancel', description='Batalkan pengumuman yang tertunda.')
    async def cancel(self, ctx: interactions.SlashContext, pengumuman_id: int) -> None:
        if not await self._ensure_repos(interaction):
            return
        repo = self.bot.announcement_repo
        assert repo is not None
        success = await repo.cancel(pengumuman_id)
        if not success:
            await ctx.send("Pengumuman tidak ditemukan atau sudah diproses.", ephemeral=True)
            return
        if self.bot.scheduler:
            self.bot.scheduler.cancel(f"announcement-{pengumuman_id}")
        await ctx.send("Pengumuman dibatalkan.", ephemeral=True)


def setup(bot: ForUS) -> None:
    Announcements(bot)
