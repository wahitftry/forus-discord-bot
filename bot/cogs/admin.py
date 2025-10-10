from __future__ import annotations

from typing import TYPE_CHECKING

import interactions

if TYPE_CHECKING:
    from bot.main import ForUS


class Admin(interactions.Extension):
    def __init__(self, bot: ForUS) -> None:
        self.bot = bot

    async def _respond_updated(self, ctx: interactions.SlashContext, message: str) -> None:
        await ctx.send(message, ephemeral=True)

    @interactions.slash_command(
        name="setup",
        description="Konfigurasi server",
        sub_cmd_name="welcome",
        sub_cmd_description="Setel channel sambutan.",
        default_member_permissions=interactions.Permissions.ADMINISTRATOR,
    )
    @interactions.slash_option(
        name="channel",
        description="Channel untuk pesan sambutan",
        opt_type=interactions.OptionType.CHANNEL,
        required=True,
    )
    async def welcome(self, ctx: interactions.SlashContext, channel: interactions.GuildText) -> None:
        if self.bot.guild_repo is None or ctx.guild is None:
            await ctx.send("Repositori belum siap atau bukan dalam server.", ephemeral=True)
            return
        await self.bot.guild_repo.upsert(ctx.guild.id, welcome_channel_id=channel.id)
        await self._respond_updated(ctx, f"Channel sambutan diset ke {channel.mention}.")

    @interactions.slash_command(
        name="setup",
        description="Konfigurasi server",
        sub_cmd_name="goodbye",
        sub_cmd_description="Setel channel perpisahan.",
        default_member_permissions=interactions.Permissions.ADMINISTRATOR,
    )
    @interactions.slash_option(
        name="channel",
        description="Channel untuk pesan perpisahan",
        opt_type=interactions.OptionType.CHANNEL,
        required=True,
    )
    async def goodbye(self, ctx: interactions.SlashContext, channel: interactions.GuildText) -> None:
        if self.bot.guild_repo is None or ctx.guild is None:
            await ctx.send("Repositori belum siap atau bukan dalam server.", ephemeral=True)
            return
        await self.bot.guild_repo.upsert(ctx.guild.id, goodbye_channel_id=channel.id)
        await self._respond_updated(ctx, f"Channel perpisahan diset ke {channel.mention}.")

    @interactions.slash_command(
        name="setup",
        description="Konfigurasi server",
        sub_cmd_name="log",
        sub_cmd_description="Setel channel log moderasi.",
        default_member_permissions=interactions.Permissions.ADMINISTRATOR,
    )
    @interactions.slash_option(
        name="channel",
        description="Channel untuk log moderasi",
        opt_type=interactions.OptionType.CHANNEL,
        required=True,
    )
    async def log(self, ctx: interactions.SlashContext, channel: interactions.GuildText) -> None:
        if self.bot.guild_repo is None or ctx.guild is None:
            await ctx.send("Repositori belum siap atau bukan dalam server.", ephemeral=True)
            return
        await self.bot.guild_repo.upsert(ctx.guild.id, log_channel_id=channel.id)
        await self._respond_updated(ctx, f"Channel log diset ke {channel.mention}.")

    @interactions.slash_command(
        name="setup",
        description="Konfigurasi server",
        sub_cmd_name="autorole",
        sub_cmd_description="Setel role otomatis saat anggota bergabung.",
        default_member_permissions=interactions.Permissions.ADMINISTRATOR,
    )
    @interactions.slash_option(
        name="role",
        description="Role yang diberikan otomatis",
        opt_type=interactions.OptionType.ROLE,
        required=True,
    )
    async def autorole(self, ctx: interactions.SlashContext, role: interactions.Role) -> None:
        if self.bot.guild_repo is None or ctx.guild is None:
            await ctx.send("Repositori belum siap atau bukan dalam server.", ephemeral=True)
            return
        await self.bot.guild_repo.upsert(ctx.guild.id, autorole_id=role.id)
        await self._respond_updated(ctx, f"Role otomatis diset ke {role.mention}.")

    @interactions.slash_command(
        name="setup",
        description="Konfigurasi server",
        sub_cmd_name="timezone",
        sub_cmd_description="Setel zona waktu default.",
        default_member_permissions=interactions.Permissions.ADMINISTRATOR,
    )
    @interactions.slash_option(
        name="zona",
        description="Zona waktu (misal: Asia/Jakarta)",
        opt_type=interactions.OptionType.STRING,
        required=True,
    )
    async def timezone(self, ctx: interactions.SlashContext, zona: str) -> None:
        if self.bot.guild_repo is None or ctx.guild is None:
            await ctx.send("Repositori belum siap atau bukan dalam server.", ephemeral=True)
            return
        await self.bot.guild_repo.upsert(ctx.guild.id, timezone=zona)
        await self._respond_updated(ctx, f"Zona waktu default diperbarui ke {zona}.")

    @interactions.slash_command(
        name="setup",
        description="Konfigurasi server",
        sub_cmd_name="ticket",
        sub_cmd_description="Setel kategori tiket.",
        default_member_permissions=interactions.Permissions.ADMINISTRATOR,
    )
    @interactions.slash_option(
        name="kategori",
        description="Kategori untuk kanal tiket",
        opt_type=interactions.OptionType.CHANNEL,
        required=True,
    )
    async def ticket(self, ctx: interactions.SlashContext, kategori: interactions.GuildCategory) -> None:
        if self.bot.guild_repo is None or ctx.guild is None:
            await ctx.send("Repositori belum siap atau bukan dalam server.", ephemeral=True)
            return
        await self.bot.guild_repo.upsert(ctx.guild.id, ticket_category_id=kategori.id)
        await self._respond_updated(ctx, f"Kategori tiket diset ke {kategori.name}.")


def setup(bot: ForUS) -> None:
    Admin(bot)
