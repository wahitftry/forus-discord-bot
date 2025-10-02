from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

if TYPE_CHECKING:
    from bot.main import ForUS


@app_commands.default_permissions(kick_members=True)
class Moderation(commands.GroupCog, name="moderasi"):
    def __init__(self, bot: ForUS) -> None:
        super().__init__()
        self.bot = bot

    async def _send_log(self, guild: discord.Guild, embed: discord.Embed) -> None:
        if self.bot.guild_repo is None:
            return
        settings = await self.bot.guild_repo.get(guild.id)
        if settings and settings.log_channel_id:
            channel = guild.get_channel(settings.log_channel_id)
            if isinstance(channel, discord.TextChannel):
                await channel.send(embed=embed)

    async def _apply_timeout(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        minutes: int,
        alasan: str | None,
        sukses_pesan: str,
    ) -> None:
        if interaction.guild is None:
            await interaction.response.send_message("Gunakan perintah ini di dalam server.", ephemeral=True)
            return
        try:
            until = discord.utils.utcnow() + timedelta(minutes=minutes)
            await member.timeout(until=until, reason=alasan)
        except discord.Forbidden:
            await interaction.response.send_message("Saya tidak memiliki izin untuk timeout pengguna ini.", ephemeral=True)
            return
        await interaction.response.send_message(sukses_pesan, ephemeral=True)

    @app_commands.command(name="kick", description="Mengeluarkan anggota dari server.")
    async def kick(self, interaction: discord.Interaction, member: discord.Member, alasan: str = "") -> None:
        if interaction.guild is None:
            await interaction.response.send_message("Gunakan perintah ini di dalam server.", ephemeral=True)
            return
        try:
            await member.kick(reason=alasan or f"Dikick oleh {interaction.user}")
        except discord.Forbidden:
            await interaction.response.send_message("Saya tidak memiliki izin untuk mengeluarkan anggota tersebut.", ephemeral=True)
            return
        embed = discord.Embed(
            title="Pengguna dikick",
            description=f"{member.mention} dikick oleh {interaction.user.mention}",
            color=discord.Color.orange(),
        )
        embed.add_field(name="Alasan", value=alasan or "Tidak ada")
        await interaction.response.send_message(embed=embed)
        await self._send_log(interaction.guild, embed)

    @app_commands.command(name="ban", description="Ban anggota dari server.")
    async def ban(self, interaction: discord.Interaction, member: discord.Member, alasan: str = "") -> None:
        if interaction.guild is None:
            await interaction.response.send_message("Gunakan perintah ini di dalam server.", ephemeral=True)
            return
        try:
            await member.ban(reason=alasan or f"Diban oleh {interaction.user}")
        except discord.Forbidden:
            await interaction.response.send_message("Saya tidak memiliki izin untuk ban anggota tersebut.", ephemeral=True)
            return
        embed = discord.Embed(
            title="Pengguna diban",
            description=f"{member.mention} diban oleh {interaction.user.mention}",
            color=discord.Color.red(),
        )
        embed.add_field(name="Alasan", value=alasan or "Tidak ada")
        await interaction.response.send_message(embed=embed)
        await self._send_log(interaction.guild, embed)

    @app_commands.command(name="unban", description="Membuka ban untuk pengguna.")
    async def unban(self, interaction: discord.Interaction, user: discord.User, alasan: str = "") -> None:
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message("Gunakan perintah ini di dalam server.", ephemeral=True)
            return
        try:
            await guild.unban(user, reason=alasan or f"Unban oleh {interaction.user}")
        except discord.NotFound:
            await interaction.response.send_message("Pengguna tidak ditemukan dalam daftar ban.", ephemeral=True)
            return
        embed = discord.Embed(
            title="Pengguna diunban",
            description=f"{user.mention} diunban oleh {interaction.user.mention}",
            color=discord.Color.green(),
        )
        embed.add_field(name="Alasan", value=alasan or "Tidak ada")
        await interaction.response.send_message(embed=embed)
        await self._send_log(guild, embed)

    @app_commands.command(name="clear", description="Menghapus sejumlah pesan terakhir.")
    @app_commands.describe(jumlah="Jumlah pesan yang ingin dihapus (1-100)")
    async def clear(self, interaction: discord.Interaction, jumlah: app_commands.Range[int, 1, 100]) -> None:
        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message("Perintah ini hanya bisa di channel teks.", ephemeral=True)
            return
        deleted = await channel.purge(limit=jumlah)
        await interaction.response.send_message(f"Berhasil menghapus {len(deleted)} pesan.", ephemeral=True)

    @app_commands.command(name="warn", description="Memberikan peringatan ke pengguna.")
    async def warn(self, interaction: discord.Interaction, member: discord.Member, alasan: str) -> None:
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message("Gunakan perintah ini di dalam server.", ephemeral=True)
            return
        if self.bot.warn_repo is None:
            await interaction.response.send_message("Repositori belum siap.", ephemeral=True)
            return
        await self.bot.warn_repo.add_warn(guild.id, member.id, interaction.user.id, alasan)
        embed = discord.Embed(
            title="Peringatan diberikan",
            description=f"{member.mention} menerima peringatan dari {interaction.user.mention}",
            color=discord.Color.yellow(),
        )
        embed.add_field(name="Alasan", value=alasan)
        await interaction.response.send_message(embed=embed)
        await self._send_log(guild, embed)

    @app_commands.command(name="warnings", description="Daftar peringatan pengguna.")
    async def warnings(self, interaction: discord.Interaction, member: discord.Member) -> None:
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message("Gunakan perintah ini di dalam server.", ephemeral=True)
            return
        if self.bot.warn_repo is None:
            await interaction.response.send_message("Repositori belum siap.", ephemeral=True)
            return
        warns = await self.bot.warn_repo.list_warns(guild.id, member.id)
        if not warns:
            await interaction.response.send_message(f"{member.mention} belum memiliki peringatan.", ephemeral=True)
            return
        embed = discord.Embed(title=f"Daftar peringatan {member.display_name}", color=discord.Color.orange())
        for warn in warns[:10]:
            embed.add_field(
                name=f"ID {warn['id']} oleh <@{warn['moderator_id']}>",
                value=f"{warn['reason']} (pada {warn['created_at']})",
                inline=False,
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="removewarn", description="Menghapus peringatan berdasarkan ID.")
    async def removewarn(self, interaction: discord.Interaction, warn_id: int) -> None:
        if self.bot.warn_repo is None:
            await interaction.response.send_message("Repositori belum siap.", ephemeral=True)
            return
        removed = await self.bot.warn_repo.remove_warn(warn_id)
        if not removed:
            await interaction.response.send_message("ID peringatan tidak ditemukan.", ephemeral=True)
            return
        await interaction.response.send_message(f"Peringatan dengan ID {warn_id} telah dihapus.", ephemeral=True)

    @app_commands.command(name="timeout", description="Nonaktifkan sementara kemampuan chat pengguna.")
    async def timeout(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        durasi_menit: app_commands.Range[int, 1, 10_080],
        alasan: str | None = None,
    ) -> None:
        await self._apply_timeout(
            interaction,
            member,
            durasi_menit,
            alasan,
            f"{member.mention} di-timeout selama {durasi_menit} menit.",
        )

    @app_commands.command(name="mute", description="Bisukan pengguna selama 60 menit.")
    async def mute(self, interaction: discord.Interaction, member: discord.Member, alasan: str | None = None) -> None:
        await self._apply_timeout(
            interaction,
            member,
            60,
            alasan,
            f"{member.mention} dibisukan selama 60 menit.",
        )

    @app_commands.command(name="unmute", description="Hapus timeout/bisuan pengguna.")
    async def unmute(self, interaction: discord.Interaction, member: discord.Member) -> None:
        try:
            await member.timeout(until=None, reason=f"Unmute oleh {interaction.user}")
        except discord.Forbidden:
            await interaction.response.send_message("Saya tidak memiliki izin untuk unmute pengguna ini.", ephemeral=True)
            return
        await interaction.response.send_message(f"{member.mention} telah di-unmute.", ephemeral=True)


async def setup(bot: ForUS) -> None:
    await bot.add_cog(Moderation(bot))
