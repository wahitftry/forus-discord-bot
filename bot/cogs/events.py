from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import discord
from discord.ext import commands

if TYPE_CHECKING:
    from bot.main import ForUS

DATA_DIR = Path(__file__).resolve().parents[2] / "bot" / "data"


class Events(commands.Cog):
    def __init__(self, bot: ForUS) -> None:
        self.bot = bot
        self.banned_words = self._load_banned_words()
        self._recent_messages: dict[int, list[float]] = {}

    def _load_banned_words(self) -> set[str]:
        file_path = DATA_DIR / "banned_words.txt"
        if not file_path.exists():
            return set()
        return {line.strip().lower() for line in file_path.read_text(encoding="utf-8").splitlines() if line.strip()}

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        if self.bot.guild_repo is None:
            return
        settings = await self.bot.guild_repo.get(member.guild.id)
        if settings:
            if settings.welcome_channel_id:
                channel = member.guild.get_channel(settings.welcome_channel_id)
                if isinstance(channel, discord.TextChannel):
                    await channel.send(f"Selamat datang {member.mention}! Jangan lupa baca peraturan ya.")
            if settings.autorole_id:
                role = member.guild.get_role(settings.autorole_id)
                if role:
                    try:
                        await member.add_roles(role, reason="Autorole sambutan")
                    except discord.Forbidden:
                        pass

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member) -> None:
        if self.bot.guild_repo is None:
            return
        settings = await self.bot.guild_repo.get(member.guild.id)
        if settings and settings.goodbye_channel_id:
            channel = member.guild.get_channel(settings.goodbye_channel_id)
            if isinstance(channel, discord.TextChannel):
                await channel.send(f"Selamat tinggal {member.display_name}. Semoga kembali lagi!")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.guild is None or message.author.bot:
            return
        content = message.content.lower()
        if any(bad_word in content for bad_word in self.banned_words):
            try:
                await message.delete()
            except discord.Forbidden:
                pass
            await message.channel.send(
                f"{message.author.mention}, kata yang kamu gunakan tidak diperbolehkan.",
                delete_after=5,
            )
            return

        # Anti-spam sederhana: lebih dari 5 pesan dalam 10 detik
        history = self._recent_messages.setdefault(message.author.id, [])
        now = message.created_at.timestamp()
        history.append(now)
        history[:] = [timestamp for timestamp in history if now - timestamp < 10]
        if len(history) > 5:
            try:
                await message.channel.set_permissions(
                    message.author,
                    send_messages=False,
                    reason="Anti-spam otomatis",
                )
            except discord.Forbidden:
                pass
            await message.channel.send(
                f"{message.author.mention} dibisukan sementara karena spam.",
                delete_after=5,
            )


async def setup(bot: ForUS) -> None:
    await bot.add_cog(Events(bot))
