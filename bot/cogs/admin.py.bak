from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

if TYPE_CHECKING:
    from bot.main import ForUS


@app_commands.default_permissions(administrator=True)
class Admin(commands.GroupCog, name="setup"):
    def __init__(self, bot: ForUS) -> None:
        super().__init__()
        self.bot = bot

    async def _respond_updated(self, interaction: discord.Interaction, message: str) -> None:
        await interaction.response.send_message(message, ephemeral=True)

    @app_commands.command(name="welcome", description="Setel channel sambutan.")
    async def welcome(self, interaction: discord.Interaction, channel: discord.TextChannel) -> None:
        if self.bot.guild_repo is None or interaction.guild is None:
            await interaction.response.send_message("Repositori belum siap atau bukan dalam server.", ephemeral=True)
            return
        await self.bot.guild_repo.upsert(interaction.guild.id, welcome_channel_id=channel.id)
        await self._respond_updated(interaction, f"Channel sambutan diset ke {channel.mention}.")

    @app_commands.command(name="goodbye", description="Setel channel perpisahan.")
    async def goodbye(self, interaction: discord.Interaction, channel: discord.TextChannel) -> None:
        if self.bot.guild_repo is None or interaction.guild is None:
            await interaction.response.send_message("Repositori belum siap atau bukan dalam server.", ephemeral=True)
            return
        await self.bot.guild_repo.upsert(interaction.guild.id, goodbye_channel_id=channel.id)
        await self._respond_updated(interaction, f"Channel perpisahan diset ke {channel.mention}.")

    @app_commands.command(name="log", description="Setel channel log moderasi.")
    async def log(self, interaction: discord.Interaction, channel: discord.TextChannel) -> None:
        if self.bot.guild_repo is None or interaction.guild is None:
            await interaction.response.send_message("Repositori belum siap atau bukan dalam server.", ephemeral=True)
            return
        await self.bot.guild_repo.upsert(interaction.guild.id, log_channel_id=channel.id)
        await self._respond_updated(interaction, f"Channel log diset ke {channel.mention}.")

    @app_commands.command(name="autorole", description="Setel role otomatis saat anggota bergabung.")
    async def autorole(self, interaction: discord.Interaction, role: discord.Role) -> None:
        if self.bot.guild_repo is None or interaction.guild is None:
            await interaction.response.send_message("Repositori belum siap atau bukan dalam server.", ephemeral=True)
            return
        await self.bot.guild_repo.upsert(interaction.guild.id, autorole_id=role.id)
        await self._respond_updated(interaction, f"Role otomatis diset ke {role.mention}.")

    @app_commands.command(name="timezone", description="Setel zona waktu default.")
    async def timezone(self, interaction: discord.Interaction, zona: str) -> None:
        if self.bot.guild_repo is None or interaction.guild is None:
            await interaction.response.send_message("Repositori belum siap atau bukan dalam server.", ephemeral=True)
            return
        await self.bot.guild_repo.upsert(interaction.guild.id, timezone=zona)
        await self._respond_updated(interaction, f"Zona waktu default diperbarui ke {zona}.")

    @app_commands.command(name="ticket", description="Setel kategori tiket.")
    async def ticket(self, interaction: discord.Interaction, kategori: discord.CategoryChannel) -> None:
        if self.bot.guild_repo is None or interaction.guild is None:
            await interaction.response.send_message("Repositori belum siap atau bukan dalam server.", ephemeral=True)
            return
        await self.bot.guild_repo.upsert(interaction.guild.id, ticket_category_id=kategori.id)
        await self._respond_updated(interaction, f"Kategori tiket diset ke {kategori.name}.")


async def setup(bot: ForUS) -> None:
    await bot.add_cog(Admin(bot))
