from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

if TYPE_CHECKING:
    from bot.main import ForUS


class Tickets(commands.GroupCog, name="ticket"):
    def __init__(self, bot: ForUS) -> None:
        super().__init__()
        self.bot = bot

    async def _get_category(self, guild: discord.Guild) -> discord.CategoryChannel | None:
        if self.bot.guild_repo is None:
            return None
        settings = await self.bot.guild_repo.get(guild.id)
        if settings and settings.ticket_category_id:
            channel = guild.get_channel(settings.ticket_category_id)
            if isinstance(channel, discord.CategoryChannel):
                return channel
        return None

    async def _create_ticket_channel(self, guild: discord.Guild, user: discord.Member) -> discord.TextChannel:
        category = await self._get_category(guild)
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(view_channel=True),
        }
        channel = await guild.create_text_channel(
            name=f"ticket-{user.name}-{user.discriminator}",
            category=category,
            overwrites=overwrites,
            reason="Tiket baru dibuat",
        )
        return channel

    @app_commands.command(name="create", description="Buat tiket bantuan.")
    async def create(self, interaction: discord.Interaction, deskripsi: str) -> None:
        guild = interaction.guild
        if guild is None or not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message("Perintah hanya untuk server.", ephemeral=True)
            return
        if self.bot.ticket_repo is None:
            await interaction.response.send_message("Repositori belum siap.", ephemeral=True)
            return
        existing = None
        if self.bot.ticket_repo:
            # Cari channel ticket aktif di guild yang dimiliki user
            for channel in guild.text_channels:
                ticket = await self.bot.ticket_repo.get_by_channel(channel.id)
                if ticket and ticket["user_id"] == interaction.user.id:
                    existing = channel
                    break
        if existing:
            await interaction.response.send_message(
                f"Anda sudah memiliki tiket aktif: {existing.mention}",
                ephemeral=True,
            )
            return
        channel = await self._create_ticket_channel(guild, interaction.user)
        ticket_id = await self.bot.ticket_repo.create(guild.id, interaction.user.id, channel.id)
        await channel.send(
            f"Halo {interaction.user.mention}! Jelaskan permasalahan Anda di sini. ID tiket: **{ticket_id}**\nDeskripsi awal: {deskripsi}"
        )
        await interaction.response.send_message(f"Tiket dibuat: {channel.mention}", ephemeral=True)

    @app_commands.command(name="close", description="Tutup tiket berjalan.")
    async def close(self, interaction: discord.Interaction) -> None:
        if self.bot.ticket_repo is None:
            await interaction.response.send_message("Repositori belum siap.", ephemeral=True)
            return
        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message("Perintah ini hanya dapat dijalankan di channel tiket.", ephemeral=True)
            return
        ticket = await self.bot.ticket_repo.get_by_channel(channel.id)
        if ticket is None:
            await interaction.response.send_message("Channel ini bukan tiket aktif.", ephemeral=True)
            return
        await self.bot.ticket_repo.close(ticket["id"])
        await channel.send("Tiket akan ditutup dalam 10 detik. Terima kasih!")
        await interaction.response.send_message("Tiket ditandai tutup.", ephemeral=True)
        await asyncio.sleep(10)
        await channel.delete(reason="Tiket ditutup")

    @app_commands.command(name="add", description="Tambahkan anggota ke tiket.")
    async def add_member(self, interaction: discord.Interaction, anggota: discord.Member) -> None:
        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message("Gunakan perintah ini di channel tiket.", ephemeral=True)
            return
        await channel.set_permissions(anggota, view_channel=True, send_messages=True)
        await interaction.response.send_message(f"{anggota.mention} ditambahkan ke tiket.", ephemeral=True)

    @app_commands.command(name="remove", description="Hapus anggota dari tiket.")
    async def remove_member(self, interaction: discord.Interaction, anggota: discord.Member) -> None:
        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message("Gunakan perintah ini di channel tiket.", ephemeral=True)
            return
        await channel.set_permissions(anggota, overwrite=None)
        await interaction.response.send_message(f"{anggota.mention} dihapus dari tiket.", ephemeral=True)


async def setup(bot: ForUS) -> None:
    await bot.add_cog(Tickets(bot))
