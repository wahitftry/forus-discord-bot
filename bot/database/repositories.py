from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional, Sequence

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


@dataclass(slots=True)
class CoupleRecord:
    id: int
    guild_id: int
    member_one_id: int
    member_two_id: int
    initiator_id: int
    pending_target_id: int
    status: str
    proposal_message: Optional[str]
    anniversary: Optional[str]
    love_points: int
    last_affection_one: Optional[str]
    last_affection_two: Optional[str]
    created_at: str
    updated_at: str
    ended_at: Optional[str]
    ended_by: Optional[int]

    def is_member(self, user_id: int) -> bool:
        return user_id in (self.member_one_id, self.member_two_id)

    def partner_id(self, user_id: int) -> Optional[int]:
        if user_id == self.member_one_id:
            return self.member_two_id
        if user_id == self.member_two_id:
            return self.member_one_id
        return None

    def last_affection_for(self, user_id: int) -> Optional[str]:
        if user_id == self.member_one_id:
            return self.last_affection_one
        if user_id == self.member_two_id:
            return self.last_affection_two
        return None


class CoupleRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def _row_to_record(self, row: Any) -> CoupleRecord:
        return CoupleRecord(
            id=int(row["id"]),
            guild_id=int(row["guild_id"]),
            member_one_id=int(row["member_one_id"]),
            member_two_id=int(row["member_two_id"]),
            initiator_id=int(row["initiator_id"]),
            pending_target_id=int(row["pending_target_id"]),
            status=str(row["status"]),
            proposal_message=row["proposal_message"],
            anniversary=row["anniversary"],
            love_points=int(row["love_points"]),
            last_affection_one=row["last_affection_one"],
            last_affection_two=row["last_affection_two"],
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
            ended_at=row["ended_at"],
            ended_by=row["ended_by"],
        )

    async def get_by_id(self, couple_id: int) -> Optional[CoupleRecord]:
        row = await self._db.fetchone("SELECT * FROM couples WHERE id = ?", couple_id)
        return None if row is None else self._row_to_record(row)

    async def get_pair(self, guild_id: int, user_id: int, partner_id: int) -> Optional[CoupleRecord]:
        member_one_id, member_two_id = sorted((user_id, partner_id))
        row = await self._db.fetchone(
            """
            SELECT * FROM couples
            WHERE guild_id = ? AND member_one_id = ? AND member_two_id = ?
            ORDER BY created_at DESC
            LIMIT 1
            """,
            guild_id,
            member_one_id,
            member_two_id,
        )
        return None if row is None else self._row_to_record(row)

    async def get_relationship(self, guild_id: int, user_id: int, statuses: Sequence[str] | None = None) -> Optional[CoupleRecord]:
        query = "SELECT * FROM couples WHERE guild_id = ? AND (member_one_id = ? OR member_two_id = ?)"
        params: list[Any] = [guild_id, user_id, user_id]
        if statuses:
            placeholders = ", ".join("?" for _ in statuses)
            query += f" AND status IN ({placeholders})"
            params.extend(statuses)
        query += " ORDER BY created_at DESC LIMIT 1"
        row = await self._db.fetchone(query, *params)
        return None if row is None else self._row_to_record(row)

    async def create_proposal(
        self,
        guild_id: int,
        initiator_id: int,
        partner_id: int,
        proposal_message: Optional[str],
    ) -> CoupleRecord:
        member_one_id, member_two_id = sorted((initiator_id, partner_id))
        await self._db.execute(
            """
            INSERT INTO couples (
                guild_id,
                member_one_id,
                member_two_id,
                initiator_id,
                pending_target_id,
                status,
                proposal_message,
                love_points,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, 'pending', ?, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """,
            guild_id,
            member_one_id,
            member_two_id,
            initiator_id,
            partner_id,
            proposal_message,
        )
        row = await self._db.fetchone("SELECT * FROM couples WHERE id = last_insert_rowid()")
        if row is None:
            raise RuntimeError("Gagal membuat data pasangan baru")
        return self._row_to_record(row)

    async def accept_proposal(self, couple_id: int, anniversary: Optional[str] = None) -> Optional[CoupleRecord]:
        if anniversary is None:
            anniversary = datetime.now(timezone.utc).date().isoformat()
        await self._db.execute(
            """
            UPDATE couples
            SET status = 'active',
                anniversary = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND status = 'pending'
            """,
            anniversary,
            couple_id,
        )
        return await self.get_by_id(couple_id)

    async def reject_proposal(self, couple_id: int, rejected_by: int) -> Optional[CoupleRecord]:
        await self._db.execute(
            """
            UPDATE couples
            SET status = 'rejected',
                updated_at = CURRENT_TIMESTAMP,
                ended_at = CURRENT_TIMESTAMP,
                ended_by = ?
            WHERE id = ? AND status = 'pending'
            """,
            rejected_by,
            couple_id,
        )
        return await self.get_by_id(couple_id)

    async def end_relationship(self, couple_id: int, ended_by: int) -> Optional[CoupleRecord]:
        await self._db.execute(
            """
            UPDATE couples
            SET status = 'ended',
                updated_at = CURRENT_TIMESTAMP,
                ended_at = CURRENT_TIMESTAMP,
                ended_by = ?
            WHERE id = ? AND status = 'active'
            """,
            ended_by,
            couple_id,
        )
        return await self.get_by_id(couple_id)

    async def update_anniversary(self, couple_id: int, anniversary: str) -> Optional[CoupleRecord]:
        await self._db.execute(
            """
            UPDATE couples
            SET anniversary = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND status = 'active'
            """,
            anniversary,
            couple_id,
        )
        return await self.get_by_id(couple_id)

    async def add_love_points(self, couple_id: int, amount: int) -> Optional[CoupleRecord]:
        await self._db.execute(
            """
            UPDATE couples
            SET love_points = love_points + ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND status = 'active'
            """,
            amount,
            couple_id,
        )
        return await self.get_by_id(couple_id)

    async def update_last_affection(self, record: CoupleRecord, user_id: int, timestamp: str) -> Optional[CoupleRecord]:
        if not record.is_member(user_id):
            raise ValueError("Pengguna bukan bagian dari pasangan ini")
        column = "last_affection_one" if user_id == record.member_one_id else "last_affection_two"
        await self._db.execute(
            f"""
            UPDATE couples
            SET {column} = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            timestamp,
            record.id,
        )
        return await self.get_by_id(record.id)

    async def list_leaderboard(self, guild_id: int, limit: int = 10) -> list[CoupleRecord]:
        rows = await self._db.fetchall(
            """
            SELECT * FROM couples
            WHERE guild_id = ? AND status = 'active'
            ORDER BY love_points DESC, created_at ASC
            LIMIT ?
            """,
            guild_id,
            limit,
        )
        return [self._row_to_record(row) for row in rows]

    async def user_has_active_or_pending(self, guild_id: int, user_id: int) -> bool:
        record = await self.get_relationship(guild_id, user_id, statuses=("pending", "active"))
        return record is not None

    async def get_pending_for_target(self, guild_id: int, user_id: int) -> Optional[CoupleRecord]:
        row = await self._db.fetchone(
            """
            SELECT * FROM couples
            WHERE guild_id = ? AND pending_target_id = ? AND status = 'pending'
            ORDER BY created_at DESC
            LIMIT 1
            """,
            guild_id,
            user_id,
        )
        return None if row is None else self._row_to_record(row)
