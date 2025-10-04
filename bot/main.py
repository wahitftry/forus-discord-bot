from __future__ import annotations

import asyncio
from pathlib import Path

import discord
from discord.ext import commands

from .config import BotConfig, load_config
from .database.core import Database
from .database import migrations
from .database.repositories import (
    GuildSettingsRepository,
    EconomyRepository,
    ReminderRepository,
    WarnRepository,
    TicketRepository,
    ShopRepository,
    CoupleRepository,
    AutomodRepository,
    AuditLogRepository,
    LevelRepository,
    AnnouncementRepository,
)
from .services.logging import setup_logging, get_logger
from .services.scheduler import Scheduler


class ForUS(commands.Bot):
    def __init__(self, config: BotConfig) -> None:
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True

        super().__init__(
            command_prefix="!",  # fallback untuk legacy
            intents=intents,
            application_id=None,
        )
        self.config = config
        self.db: Database | None = None
        self.guild_repo: GuildSettingsRepository | None = None
        self.economy_repo: EconomyRepository | None = None
        self.reminder_repo: ReminderRepository | None = None
        self.warn_repo: WarnRepository | None = None
        self.ticket_repo: TicketRepository | None = None
        self.shop_repo: ShopRepository | None = None
        self.couple_repo: CoupleRepository | None = None
        self.automod_repo: AutomodRepository | None = None
        self.audit_repo: AuditLogRepository | None = None
        self.level_repo: LevelRepository | None = None
        self.announcement_repo: AnnouncementRepository | None = None
        self.scheduler = Scheduler()
        self.log = get_logger("ForUS")

    async def setup_hook(self) -> None:
        self.log.info("Memulai inisialisasi bot...")
        await self._setup_database()
        self.scheduler.start()
        await self._load_cogs()
        await self._synchronize_commands()

    async def close(self) -> None:
        await super().close()
        if self.scheduler:
            self.scheduler.shutdown(wait=False)
        if self.db:
            await self.db.close()

    async def _setup_database(self) -> None:
        self.db = await Database.initialize(self.config.database_url)
        await migrations.run_migrations()
        self.guild_repo = GuildSettingsRepository(self.db)
        self.economy_repo = EconomyRepository(self.db)
        self.reminder_repo = ReminderRepository(self.db)
        self.warn_repo = WarnRepository(self.db)
        self.ticket_repo = TicketRepository(self.db)
        self.shop_repo = ShopRepository(self.db)
        self.couple_repo = CoupleRepository(self.db)
        self.automod_repo = AutomodRepository(self.db)
        self.audit_repo = AuditLogRepository(self.db)
        self.level_repo = LevelRepository(self.db)
        self.announcement_repo = AnnouncementRepository(self.db)

    async def _load_cogs(self) -> None:
        for extension in (
            "bot.cogs.utility",
            "bot.cogs.developer",
            "bot.cogs.moderation",
            "bot.cogs.admin",
            "bot.cogs.economy",
            "bot.cogs.reminders",
            "bot.cogs.couples",
            "bot.cogs.fun",
            "bot.cogs.tickets",
            "bot.cogs.events",
            "bot.cogs.automod",
            "bot.cogs.levels",
            "bot.cogs.announcements",
        ):
            try:
                await self.load_extension(extension)
                self.log.info("Berhasil memuat extension %s", extension)
            except Exception:  # noqa: BLE001
                self.log.exception("Gagal memuat extension %s", extension)

    async def _synchronize_commands(self) -> None:
        if self.config.guild_ids:
            await self._synchronize_guild_commands(self.config.guild_ids)
            return
        await self._synchronize_global_commands_only()

    async def _sync_commands_for_guild(self, guild_id: int) -> None:
        guild = discord.Object(id=guild_id)
        try:
            self.tree.copy_global_to(guild=guild)
            self.tree.clear_commands(guild=guild)
            await self.tree.sync(guild=guild)
            self.log.info("Sinkronisasi perintah untuk guild %s", guild_id)
        except Exception:  # noqa: BLE001
            self.log.exception("Gagal sinkronisasi command untuk guild %s", guild_id)

    async def _synchronize_guild_commands(self, guild_ids: list[int]) -> None:
        for guild_id in guild_ids:
            await self._sync_commands_for_guild(guild_id)
        try:
            self.tree.clear_commands(guild=None)
            await self.tree.sync()
            self.log.info("Membersihkan perintah global untuk mencegah duplikasi")
        except Exception:  # noqa: BLE001
            self.log.exception("Gagal membersihkan perintah global")

    async def _synchronize_global_commands_only(self) -> None:
        seen_guilds: set[int] = set()
        try:
            async for partial_guild in self.fetch_guilds(limit=None):
                if partial_guild.id in seen_guilds:
                    continue
                seen_guilds.add(partial_guild.id)
                await self._sync_commands_for_guild(partial_guild.id)
        except Exception:  # noqa: BLE001
            self.log.exception("Gagal mengambil daftar guild untuk pembersihan command")

        try:
            await self.tree.sync()
            self.log.info("Sinkronisasi perintah slash global selesai setelah pembersihan guild")
        except Exception:  # noqa: BLE001
            self.log.exception("Gagal sinkronisasi global perintah slash")


async def main() -> None:
    config = load_config(Path(".env"))
    setup_logging(config.log_level)
    bot = ForUS(config)
    async with bot:
        await bot.start(config.token)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
