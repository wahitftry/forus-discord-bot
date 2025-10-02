from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from .core import Database


@dataclass(slots=True)
class GuildSettings:
    guild_id: int
    welcome_channel_id: Optional[int]
    goodbye_channel_id: Optional[int]
    log_channel_id: Optional[int]
    autorole_id: Optional[int]
    timezone: str
    ticket_category_id: Optional[int]


class GuildSettingsRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    async def get(self, guild_id: int) -> Optional[GuildSettings]:
        row = await self._db.fetchone("SELECT * FROM guild_settings WHERE guild_id = ?", guild_id)
        if row is None:
            return None
        return GuildSettings(
            guild_id=row["guild_id"],
            welcome_channel_id=row["welcome_channel_id"],
            goodbye_channel_id=row["goodbye_channel_id"],
            log_channel_id=row["log_channel_id"],
            autorole_id=row["autorole_id"],
            timezone=row["timezone"],
            ticket_category_id=row["ticket_category_id"],
        )

    async def upsert(self, guild_id: int, **kwargs: Any) -> None:
        existing = await self.get(guild_id)
        data = {
            "welcome_channel_id": kwargs.get("welcome_channel_id", existing.welcome_channel_id if existing else None),
            "goodbye_channel_id": kwargs.get("goodbye_channel_id", existing.goodbye_channel_id if existing else None),
            "log_channel_id": kwargs.get("log_channel_id", existing.log_channel_id if existing else None),
            "autorole_id": kwargs.get("autorole_id", existing.autorole_id if existing else None),
            "timezone": kwargs.get("timezone", existing.timezone if existing else "Asia/Jakarta"),
            "ticket_category_id": kwargs.get("ticket_category_id", existing.ticket_category_id if existing else None),
        }
        if existing:
            await self._db.execute(
                """
                UPDATE guild_settings SET
                    welcome_channel_id = ?,
                    goodbye_channel_id = ?,
                    log_channel_id = ?,
                    autorole_id = ?,
                    timezone = ?,
                    ticket_category_id = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE guild_id = ?
                """,
                data["welcome_channel_id"],
                data["goodbye_channel_id"],
                data["log_channel_id"],
                data["autorole_id"],
                data["timezone"],
                data["ticket_category_id"],
                guild_id,
            )
        else:
            await self._db.execute(
                """
                INSERT INTO guild_settings (
                    guild_id,
                    welcome_channel_id,
                    goodbye_channel_id,
                    log_channel_id,
                    autorole_id,
                    timezone,
                    ticket_category_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                guild_id,
                data["welcome_channel_id"],
                data["goodbye_channel_id"],
                data["log_channel_id"],
                data["autorole_id"],
                data["timezone"],
                data["ticket_category_id"],
            )


class EconomyRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    async def get_balance(self, guild_id: int, user_id: int) -> int:
        row = await self._db.fetchone(
            "SELECT balance FROM economy WHERE guild_id = ? AND user_id = ?",
            guild_id,
            user_id,
        )
        if row is None:
            await self._db.execute(
                "INSERT INTO economy (guild_id, user_id, balance) VALUES (?, ?, 0)",
                guild_id,
                user_id,
            )
            return 0
        return int(row["balance"])

    async def update_balance(self, guild_id: int, user_id: int, amount: int) -> int:
        current = await self.get_balance(guild_id, user_id)
        new_balance = max(0, current + amount)
        await self._db.execute(
            """
            INSERT INTO economy (guild_id, user_id, balance) VALUES (?, ?, ?)
            ON CONFLICT(guild_id, user_id) DO UPDATE SET balance = excluded.balance
            """,
            guild_id,
            user_id,
            new_balance,
        )
        return new_balance

    async def set_daily_timestamp(self, guild_id: int, user_id: int, timestamp: str) -> None:
        await self._db.execute(
            """
            INSERT INTO economy (guild_id, user_id, last_daily)
            VALUES (?, ?, ?)
            ON CONFLICT(guild_id, user_id) DO UPDATE SET last_daily = excluded.last_daily
            """,
            guild_id,
            user_id,
            timestamp,
        )

    async def get_daily_timestamp(self, guild_id: int, user_id: int) -> Optional[str]:
        row = await self._db.fetchone(
            "SELECT last_daily FROM economy WHERE guild_id = ? AND user_id = ?",
            guild_id,
            user_id,
        )
        return None if row is None else row["last_daily"]

    async def top_balances(self, guild_id: int, limit: int = 10) -> list[tuple[int, int]]:
        rows = await self._db.fetchall(
            "SELECT user_id, balance FROM economy WHERE guild_id = ? ORDER BY balance DESC LIMIT ?",
            guild_id,
            limit,
        )
        return [(int(row["user_id"]), int(row["balance"])) for row in rows]


class ReminderRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    async def create(self, guild_id: int, user_id: int, message: str, remind_at: str, channel_id: Optional[int]) -> int:
        await self._db.execute(
            "INSERT INTO reminders (guild_id, user_id, message, remind_at, channel_id) VALUES (?, ?, ?, ?, ?)",
            guild_id,
            user_id,
            message,
            remind_at,
            channel_id,
        )
        row = await self._db.fetchone("SELECT last_insert_rowid() as id")
        return int(row["id"]) if row else 0

    async def due_reminders(self, timestamp: str) -> list[dict[str, Any]]:
        rows = await self._db.fetchall(
            "SELECT * FROM reminders WHERE remind_at <= ?",
            timestamp,
        )
        return [dict(row) for row in rows]

    async def delete(self, reminder_id: int) -> None:
        await self._db.execute("DELETE FROM reminders WHERE id = ?", reminder_id)

    async def list_for_user(self, guild_id: int, user_id: int) -> list[dict[str, Any]]:
        rows = await self._db.fetchall(
            "SELECT * FROM reminders WHERE guild_id = ? AND user_id = ? ORDER BY remind_at",
            guild_id,
            user_id,
        )
        return [dict(row) for row in rows]

    async def all_pending(self) -> list[dict[str, Any]]:
        rows = await self._db.fetchall("SELECT * FROM reminders")
        return [dict(row) for row in rows]


class WarnRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    async def add_warn(self, guild_id: int, user_id: int, moderator_id: int, reason: str) -> None:
        await self._db.execute(
            "INSERT INTO warns (guild_id, user_id, moderator_id, reason) VALUES (?, ?, ?, ?)",
            guild_id,
            user_id,
            moderator_id,
            reason,
        )

    async def list_warns(self, guild_id: int, user_id: int) -> list[dict[str, Any]]:
        rows = await self._db.fetchall(
            "SELECT * FROM warns WHERE guild_id = ? AND user_id = ? ORDER BY created_at DESC",
            guild_id,
            user_id,
        )
        return [dict(row) for row in rows]

    async def remove_warn(self, warn_id: int) -> bool:
        row = await self._db.fetchone("SELECT id FROM warns WHERE id = ?", warn_id)
        if row is None:
            return False
        await self._db.execute("DELETE FROM warns WHERE id = ?", warn_id)
        return True


class TicketRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    async def create(self, guild_id: int, user_id: int, channel_id: int) -> int:
        await self._db.execute(
            "INSERT INTO tickets (guild_id, user_id, channel_id, status) VALUES (?, ?, ?, 'open')",
            guild_id,
            user_id,
            channel_id,
        )
        row = await self._db.fetchone("SELECT last_insert_rowid() as id")
        return int(row["id"]) if row else 0

    async def close(self, ticket_id: int) -> None:
        await self._db.execute(
            "UPDATE tickets SET status = 'closed', closed_at = CURRENT_TIMESTAMP WHERE id = ?",
            ticket_id,
        )

    async def get_by_channel(self, channel_id: int) -> Optional[dict[str, Any]]:
        row = await self._db.fetchone(
            "SELECT * FROM tickets WHERE channel_id = ? AND status = 'open'",
            channel_id,
        )
        return None if row is None else dict(row)


class ShopRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    async def list_items(self, guild_id: int) -> list[dict[str, Any]]:
        rows = await self._db.fetchall(
            "SELECT * FROM shop_items WHERE guild_id = ? ORDER BY price",
            guild_id,
        )
        return [dict(row) for row in rows]

    async def add_item(self, guild_id: int, item_name: str, price: int, description: str, role_reward_id: Optional[int]) -> None:
        await self._db.execute(
            """
            INSERT INTO shop_items (guild_id, item_name, price, description, role_reward_id)
            VALUES (?, ?, ?, ?, ?)
            """,
            guild_id,
            item_name,
            price,
            description,
            role_reward_id,
        )

    async def get_item(self, guild_id: int, item_name: str) -> Optional[dict[str, Any]]:
        row = await self._db.fetchone(
            "SELECT * FROM shop_items WHERE guild_id = ? AND LOWER(item_name) = LOWER(?)",
            guild_id,
            item_name,
        )
        return None if row is None else dict(row)
