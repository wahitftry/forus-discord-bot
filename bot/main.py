from __future__ import annotations

import asyncio
import inspect
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import interactions
from interactions import Intents

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
from .services.presence import RichPresenceManager


class ForUS(interactions.Client):
    def __init__(self, config: BotConfig) -> None:
        intents = Intents.DEFAULT
        intents |= Intents.GUILD_MEMBERS
        intents |= Intents.MESSAGE_CONTENT

        super().__init__(
            intents=intents,
            sync_interactions=True,
            delete_unused_application_cmds=False,
            send_command_tracebacks=True,
            token=config.token,
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
        self.started_at: datetime | None = None
        self.presence_manager = RichPresenceManager(self, config.presence, version=config.bot_version)

    async def setup_hook(self) -> None:
        self.log.info("Memulai inisialisasi bot...")
        await self._setup_database()
        self.scheduler.start()
        await self._load_cogs()
        await self._synchronize_commands()
        self.started_at = datetime.now(timezone.utc)
        self.presence_manager.start()
        self.presence_manager.request_refresh()

    async def close(self) -> None:
        await self.presence_manager.close()
        if self.scheduler:
            self.scheduler.shutdown(wait=False)
        if self.db:
            await self.db.close()
        await super().close()

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
            "bot.cogs.audit",
            "bot.cogs.activity_log",
        ):
            try:
                self.load_extension(extension)
                self.log.info("Berhasil memuat extension %s", extension)
            except Exception:  # noqa: BLE001
                self.log.exception("Gagal memuat extension %s", extension)

    async def _synchronize_commands(self) -> None:
        # interactions.py handles command syncing automatically
        # with sync_interactions=True in __init__
        if self.config.guild_ids:
            # Set debug scope for guild-specific sync
            for guild_id in self.config.guild_ids:
                self.log.info("Akan sinkronisasi perintah ke guild %s", guild_id)
        else:
            self.log.info("Akan sinkronisasi perintah global")

    async def _sync_commands_for_guild(self, guild_id: int) -> None:
        # Not needed for interactions.py - handled automatically
        pass

    async def _synchronize_guild_commands(self, guild_ids: list[int]) -> None:
        # Not needed for interactions.py - handled automatically
        pass

    async def _synchronize_global_commands_only(self) -> None:
        # Not needed for interactions.py - handled automatically
        pass

    @interactions.listen()
    async def on_startup(self) -> None:
        self.log.info("Bot siap sebagai %s (ID: %s)", self.user, getattr(self.user, "id", "?"))
        self.presence_manager.request_refresh()

    @interactions.listen()
    async def on_guild_join(self, event: interactions.events.GuildJoin) -> None:
        self.presence_manager.request_refresh()

    @interactions.listen()
    async def on_guild_left(self, event: interactions.events.GuildLeft) -> None:
        self.presence_manager.request_refresh()


async def main() -> None:
    config = load_config(Path(".env"))
    setup_logging(config.log_level)
    bot = ForUS(config)
    await bot.astart()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
