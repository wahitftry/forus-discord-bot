from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import interactions

if TYPE_CHECKING:
    from bot.main import ForUS


class Tickets(interactions.Extension):
    # MANUAL REVIEW: GroupCog -> Extension with slash_command group
    def __init__(self, bot: ForUS) -> None:
        super().__init__()
        self.bot = bot

    async def _get_category(self, guild: interactions.Guild) -> discord.CategoryChannel | None:
        if self.bot.guild_repo is None:
            return None
        settings = await self.bot.guild_repo.get(guild.id)
        if settings and settings.ticket_category_id:
            channel = guild.get_channel(settings.ticket_category_id)
            if isinstance(channel, discord.CategoryChannel):
                return channel
        return None

    async def _create_ticket_channel(self, guild: interactions.Guild, user: interactions.Member) -> interactions.GuildText:
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

    @interactions.slash_command(name='create', description='Buat tiket bantuan.')
    async def create(self, ctx: interactions.SlashContext, deskripsi: str) -> None:
        guild = ctx.guild
        if guild is None or not isinstance(ctx.author, interactions.Member):
            await ctx.send("Perintah hanya untuk server.", ephemeral=True)
            return
        if self.bot.ticket_repo is None:
            await ctx.send("Repositori belum siap.", ephemeral=True)
            return
        existing = None
        if self.bot.ticket_repo:
            # Cari channel ticket aktif di guild yang dimiliki user
            for channel in guild.text_channels:
                ticket = await self.bot.ticket_repo.get_by_channel(channel.id)
                if ticket and ticket["user_id"] == ctx.author.id:
                    existing = channel
                    break
        if existing:
            await ctx.send(
                f"Anda sudah memiliki tiket aktif: {existing.mention}",
                ephemeral=True,
            )
            return
        channel = await self._create_ticket_channel(guild, ctx.author)
        ticket_id = await self.bot.ticket_repo.create(guild.id, ctx.author.id, channel.id)
        await channel.send(
            f"Halo {ctx.author.mention}! Jelaskan permasalahan Anda di sini. ID tiket: **{ticket_id}**\nDeskripsi awal: {deskripsi}"
        )
        await ctx.send(f"Tiket dibuat: {channel.mention}", ephemeral=True)

    @interactions.slash_command(name='close', description='Tutup tiket berjalan.')
    async def close(self, ctx: interactions.SlashContext) -> None:
        if self.bot.ticket_repo is None:
            await ctx.send("Repositori belum siap.", ephemeral=True)
            return
        channel = ctx.channel
        if not isinstance(channel, interactions.GuildText):
            await ctx.send("Perintah ini hanya dapat dijalankan di channel tiket.", ephemeral=True)
            return
        ticket = await self.bot.ticket_repo.get_by_channel(channel.id)
        if ticket is None:
            await ctx.send("Channel ini bukan tiket aktif.", ephemeral=True)
            return
        await self.bot.ticket_repo.close(ticket["id"])
        await channel.send("Tiket akan ditutup dalam 10 detik. Terima kasih!")
        await ctx.send("Tiket ditandai tutup.", ephemeral=True)
        await asyncio.sleep(10)
        await channel.delete(reason="Tiket ditutup")

    @interactions.slash_command(name='add', description='Tambahkan anggota ke tiket.')
    async def add_member(self, ctx: interactions.SlashContext, anggota: interactions.Member) -> None:
        channel = ctx.channel
        if not isinstance(channel, interactions.GuildText):
            await ctx.send("Gunakan perintah ini di channel tiket.", ephemeral=True)
            return
        await channel.set_permissions(anggota, view_channel=True, send_messages=True)
        await ctx.send(f"{anggota.mention} ditambahkan ke tiket.", ephemeral=True)

    @interactions.slash_command(name='remove', description='Hapus anggota dari tiket.')
    async def remove_member(self, ctx: interactions.SlashContext, anggota: interactions.Member) -> None:
        channel = ctx.channel
        if not isinstance(channel, interactions.GuildText):
            await ctx.send("Gunakan perintah ini di channel tiket.", ephemeral=True)
            return
        await channel.set_permissions(anggota, overwrite=None)
        await ctx.send(f"{anggota.mention} dihapus dari tiket.", ephemeral=True)


def setup(bot: ForUS) -> None:
    Tickets(bot)
