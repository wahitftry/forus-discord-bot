from __future__ import annotations

import platform
import time
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

if TYPE_CHECKING:
    from bot.main import ForUS


class Utility(commands.Cog):
    def __init__(self, bot: ForUS) -> None:
        self.bot = bot
        self.launch_time = time.time()

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


async def setup(bot: ForUS) -> None:
    await bot.add_cog(Utility(bot))
