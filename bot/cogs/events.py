from __future__ import annotations

import random
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

import interactions

if TYPE_CHECKING:
    from bot.main import ForUS

DATA_DIR = Path(__file__).resolve().parents[2] / "bot" / "data"


from bot.database.repositories import AutomodRule, LevelProgress
from bot.services.automod import AutomodEngine
from bot.services.cache import TTLCache


class Events(interactions.Extension):
    def __init__(self, bot: ForUS) -> None:
        self.bot = bot
        self.banned_words = self._load_banned_words()
        self._recent_messages: dict[int, list[float]] = {}
        self._automod_engine = AutomodEngine()
        self._automod_cache = TTLCache(ttl=30)

    def _load_banned_words(self) -> set[str]:
        file_path = DATA_DIR / "banned_words.txt"
        if not file_path.exists():
            return set()
        return {line.strip().lower() for line in file_path.read_text(encoding="utf-8").splitlines() if line.strip()}

    @interactions.listen()
    async def on_member_join(self, member: interactions.Member) -> None:
        if self.bot.guild_repo is None:
            return
        settings = await self.bot.guild_repo.get(member.guild.id)
        if settings:
            if settings.welcome_channel_id:
                channel = member.guild.get_channel(settings.welcome_channel_id)
                if isinstance(channel, interactions.GuildText):
                    await channel.send(f"Selamat datang {member.mention}! Jangan lupa baca peraturan ya.")
            if settings.autorole_id:
                role = member.guild.get_role(settings.autorole_id)
                if role:
                    try:
                        await member.add_roles(role, reason="Autorole sambutan")
                    except discord.Forbidden:
                        pass

    @interactions.listen()
    async def on_member_remove(self, member: interactions.Member) -> None:
        if self.bot.guild_repo is None:
            return
        settings = await self.bot.guild_repo.get(member.guild.id)
        if settings and settings.goodbye_channel_id:
            channel = member.guild.get_channel(settings.goodbye_channel_id)
            if isinstance(channel, interactions.GuildText):
                await channel.send(f"Selamat tinggal {member.display_name}. Semoga kembali lagi!")

    @interactions.listen()
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
            return

        if await self._handle_automod(message):
            return

        await self._award_level_xp(message)

    async def _handle_automod(self, message: discord.Message) -> bool:
        if self.bot.automod_repo is None or message.guild is None:
            return False

        rules = await self._get_automod_rules(message.guild.id)
        if not rules:
            return False

        mention_count = len(message.mentions) + len(message.role_mentions)
        if message.mention_everyone:
            mention_count += 1

        violations = self._automod_engine.evaluate(
            content=message.content,
            mention_count=mention_count,
            rules=rules,
        )
        if not violations:
            return False

        violation = violations[0]
        try:
            await message.delete()
        except discord.Forbidden:
            pass

        warning_text = f"{message.author.mention}, pesanmu dihapus: {violation.reason}"
        await message.channel.send(warning_text, delete_after=6)

        log_channel = await self._get_log_channel(message.guild)
        if log_channel:
            embed = interactions.Embed(
                title="Automod",
                description=violation.reason,
                color=interactions.Color.from_hex("#ED4245"),
                timestamp=datetime.now(timezone.utc),
            )
            embed.add_field(name="Pengguna", value=message.author.mention)
            embed.add_field(name="Channel", value=message.channel.mention)
            embed.add_field(name="Aturan", value=violation.rule_type)
            if message.content:
                truncated = message.content[:200] + ("…" if len(message.content) > 200 else "")
                embed.add_field(name="Pesan", value=truncated, inline=False)
            await log_channel.send(embed=embed)

        if self.bot.audit_repo is not None:
            await self.bot.audit_repo.add_entry(
                message.guild.id,
                action="automod.violation",
                actor_id=message.author.id,
                target_id=message.channel.id,
                context=violation.rule_type,
            )

        return True

    async def _get_log_channel(self, guild: interactions.Guild) -> interactions.GuildText | None:
        if self.bot.guild_repo is None:
            return None
        settings = await self.bot.guild_repo.get(guild.id)
        if settings and settings.log_channel_id:
            channel = guild.get_channel(settings.log_channel_id)
            if isinstance(channel, interactions.GuildText):
                return channel
        return None

    async def _get_automod_rules(self, guild_id: int) -> list[AutomodRule]:
        cache_key = f"automod:{guild_id}"

        repo = self.bot.automod_repo
        if repo is None:
            return []

        async def _loader():
            data = await repo.list_rules(guild_id)
            return tuple(data)

        cached = await self._automod_cache.get_or_set(cache_key, _loader)
        return list(cached)

    async def _award_level_xp(self, message: discord.Message) -> None:
        if self.bot.level_repo is None or message.guild is None:
            return
        if len(message.content.strip()) < 3:
            return
        reward = random.randint(15, 25)
        progress = await self.bot.level_repo.add_xp(message.guild.id, message.author.id, reward)
        if progress.leveled_up:
            await self._handle_level_up(message, progress)

    async def _handle_level_up(self, message: discord.Message, progress: LevelProgress) -> None:
        guild = message.guild
        if guild is None:
            return
        embed = interactions.Embed(
            title="Level Up!",
            description=f"{message.author.mention} mencapai level {progress.profile.level}!",
            color=interactions.Color.from_hex("#E67E22"),
            timestamp=datetime.now(timezone.utc),
        )
        embed.add_field(
            name="XP",
            value=f"Total {progress.profile.xp} XP — butuh {progress.xp_remaining} lagi untuk level berikutnya.",
        )
        await message.channel.send(embed=embed)

        if self.bot.level_repo is None:
            return
        reward = await self.bot.level_repo.get_reward_for_level(guild.id, progress.profile.level)
        if reward is None:
            return
        role = guild.get_role(reward.role_id)
        if role and isinstance(message.author, interactions.Member) and role not in message.author.roles:
            try:
                await message.author.add_roles(role, reason="Hadiah level")
            except discord.Forbidden:
                pass

    @interactions.listen()
    async def on_automod_rules_updated(self, guild_id: int) -> None:
        await self._automod_cache.invalidate(f"automod:{guild_id}")


def setup(bot: ForUS) -> None:
    Events(bot)
