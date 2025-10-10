from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

import interactions

if TYPE_CHECKING:
    from bot.main import ForUS


class Moderation(interactions.Extension):
    # MANUAL REVIEW: GroupCog -> Extension with slash_command group
    def __init__(self, bot: ForUS) -> None:
        super().__init__()
        self.bot = bot

    async def _send_log(self, guild: interactions.Guild, embed: interactions.Embed) -> None:
        if self.bot.guild_repo is None:
            return
        settings = await self.bot.guild_repo.get(guild.id)
        if settings and settings.log_channel_id:
            channel = guild.get_channel(settings.log_channel_id)
            if isinstance(channel, interactions.GuildText):
                await channel.send(embed=embed)

    async def _apply_timeout(
        self,
        ctx: interactions.SlashContext,
        member: interactions.Member,
        minutes: int,
        alasan: str | None,
        sukses_pesan: str,
    ) -> None:
        if ctx.guild is None:
            await ctx.send("Gunakan perintah ini di dalam server.", ephemeral=True)
            return
        try:
            until = discord.utils.utcnow() + timedelta(minutes=minutes)
            await member.timeout(until=until, reason=alasan)
        except discord.Forbidden:
            await ctx.send("Saya tidak memiliki izin untuk timeout pengguna ini.", ephemeral=True)
            return
        await ctx.send(sukses_pesan, ephemeral=True)

    @interactions.slash_command(name='kick', description='Mengeluarkan anggota dari server.')
    async def kick(self, ctx: interactions.SlashContext, member: interactions.Member, alasan: str = "") -> None:
        if ctx.guild is None:
            await ctx.send("Gunakan perintah ini di dalam server.", ephemeral=True)
            return
        try:
            await member.kick(reason=alasan or f"Dikick oleh {ctx.author}")
        except discord.Forbidden:
            await ctx.send("Saya tidak memiliki izin untuk mengeluarkan anggota tersebut.", ephemeral=True)
            return
        embed = interactions.Embed(
            title="Pengguna dikick",
            description=f"{member.mention} dikick oleh {ctx.author.mention}",
            color=interactions.Color.from_hex("#E67E22"),
        )
        embed.add_field(name="Alasan", value=alasan or "Tidak ada")
        await ctx.send(embed=embed)
        await self._send_log(ctx.guild, embed)

    @interactions.slash_command(name='ban', description='Ban anggota dari server.')
    async def ban(self, ctx: interactions.SlashContext, member: interactions.Member, alasan: str = "") -> None:
        if ctx.guild is None:
            await ctx.send("Gunakan perintah ini di dalam server.", ephemeral=True)
            return
        try:
            await member.ban(reason=alasan or f"Diban oleh {ctx.author}")
        except discord.Forbidden:
            await ctx.send("Saya tidak memiliki izin untuk ban anggota tersebut.", ephemeral=True)
            return
        embed = interactions.Embed(
            title="Pengguna diban",
            description=f"{member.mention} diban oleh {ctx.author.mention}",
            color=interactions.Color.from_hex("#ED4245"),
        )
        embed.add_field(name="Alasan", value=alasan or "Tidak ada")
        await ctx.send(embed=embed)
        await self._send_log(ctx.guild, embed)

    @interactions.slash_command(name='unban', description='Membuka ban untuk pengguna.')
    async def unban(self, ctx: interactions.SlashContext, user: interactions.User, alasan: str = "") -> None:
        guild = ctx.guild
        if guild is None:
            await ctx.send("Gunakan perintah ini di dalam server.", ephemeral=True)
            return
        try:
            await guild.unban(user, reason=alasan or f"Unban oleh {ctx.author}")
        except discord.NotFound:
            await ctx.send("Pengguna tidak ditemukan dalam daftar ban.", ephemeral=True)
            return
        embed = interactions.Embed(
            title="Pengguna diunban",
            description=f"{user.mention} diunban oleh {ctx.author.mention}",
            color=interactions.Color.from_hex("#2ECC71"),
        )
        embed.add_field(name="Alasan", value=alasan or "Tidak ada")
        await ctx.send(embed=embed)
        await self._send_log(guild, embed)

    @interactions.slash_command(name='clear', description='Menghapus sejumlah pesan terakhir.')
    @interactions.slash_option(
        name="jumlah",
        description="Jumlah pesan yang ingin dihapus (1-100)",
        opt_type=interactions.OptionType.INTEGER,
        min_value=1,
        max_value=100,
        required=True,
    )
    async def clear(self, ctx: interactions.SlashContext, jumlah: int) -> None:
        channel = ctx.channel
        if not isinstance(channel, interactions.GuildText):
            await ctx.send("Perintah ini hanya bisa di channel teks.", ephemeral=True)
            return
        await ctx.defer(ephemeral=True)
        try:
            deleted = await channel.purge(limit=jumlah)
        except discord.Forbidden:
            await ctx.send("Saya tidak memiliki izin untuk menghapus pesan di channel ini.", ephemeral=True)
            return
        except discord.HTTPException:
            await ctx.send("Terjadi kesalahan saat menghapus pesan. Coba lagi nanti.", ephemeral=True)
            return
        await ctx.send(f"Berhasil menghapus {len(deleted)} pesan.", ephemeral=True)

    @interactions.slash_command(name='warn', description='Memberikan peringatan ke pengguna.')
    async def warn(self, ctx: interactions.SlashContext, member: interactions.Member, alasan: str) -> None:
        guild = ctx.guild
        if guild is None:
            await ctx.send("Gunakan perintah ini di dalam server.", ephemeral=True)
            return
        if self.bot.warn_repo is None:
            await ctx.send("Repositori belum siap.", ephemeral=True)
            return
        await self.bot.warn_repo.add_warn(guild.id, member.id, ctx.author.id, alasan)
        embed = interactions.Embed(
            title="Peringatan diberikan",
            description=f"{member.mention} menerima peringatan dari {ctx.author.mention}",
            color=interactions.Color.from_hex("#FEE75C"),
        )
        embed.add_field(name="Alasan", value=alasan)
        await ctx.send(embed=embed)
        await self._send_log(guild, embed)

    @interactions.slash_command(name='warnings', description='Daftar peringatan pengguna.')
    async def warnings(self, ctx: interactions.SlashContext, member: interactions.Member) -> None:
        guild = ctx.guild
        if guild is None:
            await ctx.send("Gunakan perintah ini di dalam server.", ephemeral=True)
            return
        if self.bot.warn_repo is None:
            await ctx.send("Repositori belum siap.", ephemeral=True)
            return
        warns = await self.bot.warn_repo.list_warns(guild.id, member.id)
        if not warns:
            await ctx.send(f"{member.mention} belum memiliki peringatan.", ephemeral=True)
            return
        embed = interactions.Embed(title=f"Daftar peringatan {member.display_name}", color=interactions.Color.from_hex("#E67E22"))
        for warn in warns[:10]:
            embed.add_field(
                name=f"ID {warn['id']} oleh <@{warn['moderator_id']}>",
                value=f"{warn['reason']} (pada {warn['created_at']})",
                inline=False,
            )
        await ctx.send(embed=embed, ephemeral=True)

    @interactions.slash_command(name='removewarn', description='Menghapus peringatan berdasarkan ID.')
    async def removewarn(self, ctx: interactions.SlashContext, warn_id: int) -> None:
        if self.bot.warn_repo is None:
            await ctx.send("Repositori belum siap.", ephemeral=True)
            return
        removed = await self.bot.warn_repo.remove_warn(warn_id)
        if not removed:
            await ctx.send("ID peringatan tidak ditemukan.", ephemeral=True)
            return
        await ctx.send(f"Peringatan dengan ID {warn_id} telah dihapus.", ephemeral=True)

    @interactions.slash_command(name='timeout', description='Nonaktifkan sementara kemampuan chat pengguna.')
    @interactions.slash_option(
        name="member",
        description="Member yang akan di-timeout",
        opt_type=interactions.OptionType.USER,
        required=True,
    )
    @interactions.slash_option(
        name="durasi_menit",
        description="Durasi timeout dalam menit (1-10080)",
        opt_type=interactions.OptionType.INTEGER,
        min_value=1,
        max_value=10_080,
        required=True,
    )
    @interactions.slash_option(
        name="alasan",
        description="Alasan timeout",
        opt_type=interactions.OptionType.STRING,
        required=False,
    )
    async def timeout(
        self,
        ctx: interactions.SlashContext,
        member: interactions.Member,
        durasi_menit: int,
        alasan: str | None = None,
    ) -> None:
        await self._apply_timeout(
            interaction,
            member,
            durasi_menit,
            alasan,
            f"{member.mention} di-timeout selama {durasi_menit} menit.",
        )

    @interactions.slash_command(name='mute', description='Bisukan pengguna selama 60 menit.')
    async def mute(self, ctx: interactions.SlashContext, member: interactions.Member, alasan: str | None = None) -> None:
        await self._apply_timeout(
            interaction,
            member,
            60,
            alasan,
            f"{member.mention} dibisukan selama 60 menit.",
        )

    @interactions.slash_command(name='unmute', description='Hapus timeout/bisuan pengguna.')
    async def unmute(self, ctx: interactions.SlashContext, member: interactions.Member) -> None:
        try:
            await member.timeout(until=None, reason=f"Unmute oleh {ctx.author}")
        except discord.Forbidden:
            await ctx.send("Saya tidak memiliki izin untuk unmute pengguna ini.", ephemeral=True)
            return
        await ctx.send(f"{member.mention} telah di-unmute.", ephemeral=True)


def setup(bot: ForUS) -> None:
    Moderation(bot)
