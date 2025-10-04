from __future__ import annotations

import json

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any, Iterable, Optional, Sequence

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
    activity_log_channel_id: Optional[int]
    activity_log_enabled: bool
    activity_log_disabled_events: list[str]

    def effective_activity_channel(self) -> Optional[int]:
        return self.activity_log_channel_id or self.log_channel_id

    def is_activity_category_enabled(self, category: str) -> bool:
        if not self.activity_log_enabled:
            return False
        return category not in self.activity_log_disabled_events


class GuildSettingsRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    async def get(self, guild_id: int) -> Optional[GuildSettings]:
        row = await self._db.fetchone("SELECT * FROM guild_settings WHERE guild_id = ?", guild_id)
        if row is None:
            return None
        row_keys = row.keys()
        disabled_raw = row["activity_log_disabled_events"] if "activity_log_disabled_events" in row_keys else "[]"
        try:
            disabled_events = [
                str(item)
                for item in json.loads(disabled_raw)  # type: ignore[arg-type]
                if isinstance(item, str)
            ]
        except (TypeError, json.JSONDecodeError):
            disabled_events = []

        return GuildSettings(
            guild_id=row["guild_id"],
            welcome_channel_id=row["welcome_channel_id"],
            goodbye_channel_id=row["goodbye_channel_id"],
            log_channel_id=row["log_channel_id"],
            autorole_id=row["autorole_id"],
            timezone=row["timezone"],
            ticket_category_id=row["ticket_category_id"],
            activity_log_channel_id=row["activity_log_channel_id"] if "activity_log_channel_id" in row_keys else None,
            activity_log_enabled=bool(row["activity_log_enabled"]) if "activity_log_enabled" in row_keys else True,
            activity_log_disabled_events=disabled_events,
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
        data["activity_log_channel_id"] = kwargs.get(
            "activity_log_channel_id",
            existing.activity_log_channel_id if existing else None,
        )
        activity_enabled_input = kwargs.get(
            "activity_log_enabled",
            existing.activity_log_enabled if existing else True,
        )
        data["activity_log_enabled"] = 1 if bool(activity_enabled_input) else 0

        disabled_input = kwargs.get(
            "activity_log_disabled_events",
            existing.activity_log_disabled_events if existing else [],
        )

        if isinstance(disabled_input, str):
            try:
                disabled_events = [
                    str(item)
                    for item in json.loads(disabled_input)  # type: ignore[arg-type]
                    if isinstance(item, str)
                ]
            except (TypeError, json.JSONDecodeError):
                disabled_events = []
        else:
            disabled_events = [str(item) for item in disabled_input]

        data["activity_log_disabled_events"] = json.dumps(sorted(set(disabled_events)))

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
                    activity_log_channel_id = ?,
                    activity_log_enabled = ?,
                    activity_log_disabled_events = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE guild_id = ?
                """,
                data["welcome_channel_id"],
                data["goodbye_channel_id"],
                data["log_channel_id"],
                data["autorole_id"],
                data["timezone"],
                data["ticket_category_id"],
                data["activity_log_channel_id"],
                data["activity_log_enabled"],
                data["activity_log_disabled_events"],
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
                    ticket_category_id,
                    activity_log_channel_id,
                    activity_log_enabled,
                    activity_log_disabled_events
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                guild_id,
                data["welcome_channel_id"],
                data["goodbye_channel_id"],
                data["log_channel_id"],
                data["autorole_id"],
                data["timezone"],
                data["ticket_category_id"],
                data["activity_log_channel_id"],
                data["activity_log_enabled"],
                data["activity_log_disabled_events"],
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


@dataclass(slots=True)
class CoupleProfile:
    couple_id: int
    title: Optional[str]
    theme_color: Optional[str]
    love_song: Optional[str]
    bio: Optional[str]
    current_mood: Optional[str]
    last_checkin_date: Optional[str]
    checkin_streak: int
    updated_at: str


@dataclass(slots=True)
class CoupleMemory:
    id: int
    couple_id: int
    title: str
    description: Optional[str]
    created_by: int
    created_at: str


@dataclass(slots=True)
class CoupleGift:
    id: int
    couple_id: int
    gift_key: str
    given_by: int
    message: Optional[str]
    love_points_awarded: int
    cost: int
    created_at: str


@dataclass(slots=True)
class CoupleMilestone:
    id: int
    couple_id: int
    milestone_key: str
    achieved_at: str


@dataclass(slots=True)
class CoupleCheckin:
    id: int
    couple_id: int
    checkin_date: str
    member_one_checked: bool
    member_two_checked: bool
    updated_at: str


@dataclass(slots=True)
class CheckinResult:
    status: str
    profile: CoupleProfile
    checkin: CoupleCheckin
    streak_updated: bool


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

    def _row_to_profile(self, row: Any) -> CoupleProfile:
        return CoupleProfile(
            couple_id=int(row["couple_id"]),
            title=row["title"],
            theme_color=row["theme_color"],
            love_song=row["love_song"],
            bio=row["bio"],
            current_mood=row["current_mood"],
            last_checkin_date=row["last_checkin_date"],
            checkin_streak=int(row["checkin_streak"] or 0),
            updated_at=str(row["updated_at"]),
        )

    def _row_to_memory(self, row: Any) -> CoupleMemory:
        return CoupleMemory(
            id=int(row["id"]),
            couple_id=int(row["couple_id"]),
            title=str(row["title"]),
            description=row["description"],
            created_by=int(row["created_by"]),
            created_at=str(row["created_at"]),
        )

    def _row_to_gift(self, row: Any) -> CoupleGift:
        return CoupleGift(
            id=int(row["id"]),
            couple_id=int(row["couple_id"]),
            gift_key=str(row["gift_key"]),
            given_by=int(row["given_by"]),
            message=row["message"],
            love_points_awarded=int(row["love_points_awarded"]),
            cost=int(row["cost"]),
            created_at=str(row["created_at"]),
        )

    def _row_to_milestone(self, row: Any) -> CoupleMilestone:
        return CoupleMilestone(
            id=int(row["id"]),
            couple_id=int(row["couple_id"]),
            milestone_key=str(row["milestone_key"]),
            achieved_at=str(row["achieved_at"]),
        )

    def _row_to_checkin(self, row: Any) -> CoupleCheckin:
        return CoupleCheckin(
            id=int(row["id"]),
            couple_id=int(row["couple_id"]),
            checkin_date=str(row["checkin_date"]),
            member_one_checked=bool(row["member_one_checked"]),
            member_two_checked=bool(row["member_two_checked"]),
            updated_at=str(row["updated_at"]),
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

    async def get_profile(self, couple_id: int) -> CoupleProfile:
        row = await self._db.fetchone(
            "SELECT * FROM couple_profiles WHERE couple_id = ?",
            couple_id,
        )
        if row is None:
            await self._db.execute(
                "INSERT INTO couple_profiles (couple_id) VALUES (?)",
                couple_id,
            )
            row = await self._db.fetchone(
                "SELECT * FROM couple_profiles WHERE couple_id = ?",
                couple_id,
            )
        assert row is not None
        return self._row_to_profile(row)

    async def update_profile(self, couple_id: int, **fields: Any) -> CoupleProfile:
        allowed = {
            "title",
            "theme_color",
            "love_song",
            "bio",
            "current_mood",
            "last_checkin_date",
            "checkin_streak",
        }
        updates = {key: value for key, value in fields.items() if key in allowed}
        if not updates:
            return await self.get_profile(couple_id)
        set_clause = ", ".join(f"{key} = ?" for key in updates)
        params = list(updates.values())
        params.append(couple_id)
        await self._db.execute(
            f"""
            UPDATE couple_profiles
            SET {set_clause},
                updated_at = CURRENT_TIMESTAMP
            WHERE couple_id = ?
            """,
            *params,
        )
        return await self.get_profile(couple_id)

    async def list_memories(self, couple_id: int, limit: int = 10) -> list[CoupleMemory]:
        rows = await self._db.fetchall(
            """
            SELECT * FROM couple_memories
            WHERE couple_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            couple_id,
            limit,
        )
        return [self._row_to_memory(row) for row in rows]

    async def get_latest_memory(self, couple_id: int) -> Optional[CoupleMemory]:
        row = await self._db.fetchone(
            """
            SELECT * FROM couple_memories
            WHERE couple_id = ?
            ORDER BY created_at DESC
            LIMIT 1
            """,
            couple_id,
        )
        return None if row is None else self._row_to_memory(row)

    async def count_memories(self, couple_id: int) -> int:
        row = await self._db.fetchone(
            "SELECT COUNT(*) as total FROM couple_memories WHERE couple_id = ?",
            couple_id,
        )
        return int(row["total"]) if row is not None else 0

    async def add_memory(self, couple_id: int, title: str, description: Optional[str], created_by: int) -> CoupleMemory:
        await self._db.execute(
            """
            INSERT INTO couple_memories (couple_id, title, description, created_by)
            VALUES (?, ?, ?, ?)
            """,
            couple_id,
            title,
            description,
            created_by,
        )
        row = await self._db.fetchone("SELECT * FROM couple_memories WHERE id = last_insert_rowid()")
        if row is None:
            raise RuntimeError("Gagal menambahkan memori pasangan")
        return self._row_to_memory(row)

    async def delete_memory(self, couple_id: int, memory_id: int) -> bool:
        exists = await self._db.fetchone(
            "SELECT id FROM couple_memories WHERE id = ? AND couple_id = ?",
            memory_id,
            couple_id,
        )
        if exists is None:
            return False
        await self._db.execute(
            "DELETE FROM couple_memories WHERE id = ?",
            memory_id,
        )
        return True

    async def list_gifts(self, couple_id: int, limit: int = 10) -> list[CoupleGift]:
        rows = await self._db.fetchall(
            """
            SELECT * FROM couple_gifts
            WHERE couple_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            couple_id,
            limit,
        )
        return [self._row_to_gift(row) for row in rows]

    async def add_gift(
        self,
        couple_id: int,
        gift_key: str,
        given_by: int,
        message: Optional[str],
        love_points_awarded: int,
        cost: int,
    ) -> CoupleGift:
        await self._db.execute(
            """
            INSERT INTO couple_gifts (couple_id, gift_key, given_by, message, love_points_awarded, cost)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            couple_id,
            gift_key,
            given_by,
            message,
            love_points_awarded,
            cost,
        )
        row = await self._db.fetchone("SELECT * FROM couple_gifts WHERE id = last_insert_rowid()")
        if row is None:
            raise RuntimeError("Gagal mencatat hadiah pasangan")
        return self._row_to_gift(row)

    async def list_milestones(self, couple_id: int) -> list[CoupleMilestone]:
        rows = await self._db.fetchall(
            """
            SELECT * FROM couple_milestones
            WHERE couple_id = ?
            ORDER BY achieved_at ASC
            """,
            couple_id,
        )
        return [self._row_to_milestone(row) for row in rows]

    async def has_milestone(self, couple_id: int, milestone_key: str) -> bool:
        row = await self._db.fetchone(
            "SELECT id FROM couple_milestones WHERE couple_id = ? AND milestone_key = ?",
            couple_id,
            milestone_key,
        )
        return row is not None

    async def record_milestone(self, couple_id: int, milestone_key: str) -> CoupleMilestone:
        await self._db.execute(
            """
            INSERT OR IGNORE INTO couple_milestones (couple_id, milestone_key)
            VALUES (?, ?)
            """,
            couple_id,
            milestone_key,
        )
        row = await self._db.fetchone(
            "SELECT * FROM couple_milestones WHERE couple_id = ? AND milestone_key = ?",
            couple_id,
            milestone_key,
        )
        if row is None:
            raise RuntimeError("Gagal mencatat milestone pasangan")
        return self._row_to_milestone(row)

    async def list_checkins(self, couple_id: int, limit: int = 7) -> list[CoupleCheckin]:
        rows = await self._db.fetchall(
            """
            SELECT * FROM couple_checkins
            WHERE couple_id = ?
            ORDER BY checkin_date DESC
            LIMIT ?
            """,
            couple_id,
            limit,
        )
        return [self._row_to_checkin(row) for row in rows]

    async def record_checkin(self, record: CoupleRecord, user_id: int) -> CheckinResult:
        if not record.is_member(user_id):
            raise ValueError("Pengguna bukan bagian dari pasangan ini")

        profile = await self.get_profile(record.id)
        today = date.today()
        today_str = today.isoformat()

        if profile.last_checkin_date:
            try:
                last_date = date.fromisoformat(profile.last_checkin_date)
            except ValueError:
                last_date = None
        else:
            last_date = None

        if last_date and last_date < today - timedelta(days=1) and profile.checkin_streak != 0:
            profile = await self.update_profile(record.id, checkin_streak=0)

        is_member_one = user_id == record.member_one_id
        column = "member_one_checked" if is_member_one else "member_two_checked"

        row = await self._db.fetchone(
            "SELECT * FROM couple_checkins WHERE couple_id = ? AND checkin_date = ?",
            record.id,
            today_str,
        )

        if row is None:
            member_one_checked = 1 if is_member_one else 0
            member_two_checked = 1 if not is_member_one else 0
            await self._db.execute(
                """
                INSERT INTO couple_checkins (couple_id, checkin_date, member_one_checked, member_two_checked)
                VALUES (?, ?, ?, ?)
                """,
                record.id,
                today_str,
                member_one_checked,
                member_two_checked,
            )
            row = await self._db.fetchone("SELECT * FROM couple_checkins WHERE id = last_insert_rowid()")
            assert row is not None
            checkin = self._row_to_checkin(row)
        else:
            checkin = self._row_to_checkin(row)
            already_checked = (checkin.member_one_checked and is_member_one) or (checkin.member_two_checked and not is_member_one)
            if already_checked:
                return CheckinResult("already", profile, checkin, False)
            await self._db.execute(
                f"""
                UPDATE couple_checkins
                SET {column} = 1,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                checkin.id,
            )
            row = await self._db.fetchone(
                "SELECT * FROM couple_checkins WHERE id = ?",
                checkin.id,
            )
            assert row is not None
            checkin = self._row_to_checkin(row)

        if checkin.member_one_checked and checkin.member_two_checked:
            new_streak = 1
            if last_date == today:
                new_streak = profile.checkin_streak or 1
            elif last_date == today - timedelta(days=1):
                new_streak = profile.checkin_streak + 1 if profile.checkin_streak else 1
            else:
                new_streak = 1

            profile = await self.update_profile(
                record.id,
                checkin_streak=new_streak,
                last_checkin_date=today_str,
            )
            return CheckinResult("completed", profile, checkin, True)

        return CheckinResult("awaiting_partner", profile, checkin, False)

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


@dataclass(slots=True)
class AutomodRule:
    guild_id: int
    rule_type: str
    payload: dict[str, Any]
    is_active: bool


class AutomodRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def _row_to_rule(self, row: Any) -> AutomodRule:
        try:
            payload = json.loads(row["value_json"])
        except (TypeError, json.JSONDecodeError):
            payload = {}
        return AutomodRule(
            guild_id=int(row["guild_id"]),
            rule_type=str(row["rule_type"]),
            payload=payload,
            is_active=bool(row["is_active"]),
        )

    async def set_rule(
        self,
        guild_id: int,
        rule_type: str,
        payload: dict[str, Any],
        *,
        is_active: bool = True,
    ) -> AutomodRule:
        value_json = json.dumps(payload)
        await self._db.execute(
            """
            INSERT INTO automod_rules (guild_id, rule_type, value_json, is_active)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(guild_id, rule_type) DO UPDATE SET
                value_json = excluded.value_json,
                is_active = excluded.is_active
            """,
            guild_id,
            rule_type,
            value_json,
            1 if is_active else 0,
        )
        row = await self._db.fetchone(
            "SELECT * FROM automod_rules WHERE guild_id = ? AND rule_type = ?",
            guild_id,
            rule_type,
        )
        assert row is not None
        return self._row_to_rule(row)

    async def set_active(self, guild_id: int, rule_type: str, is_active: bool) -> None:
        await self._db.execute(
            """
            UPDATE automod_rules
            SET is_active = ?
            WHERE guild_id = ? AND rule_type = ?
            """,
            1 if is_active else 0,
            guild_id,
            rule_type,
        )

    async def get_rule(self, guild_id: int, rule_type: str) -> Optional[AutomodRule]:
        row = await self._db.fetchone(
            "SELECT * FROM automod_rules WHERE guild_id = ? AND rule_type = ?",
            guild_id,
            rule_type,
        )
        return None if row is None else self._row_to_rule(row)

    async def list_rules(self, guild_id: int) -> list[AutomodRule]:
        rows = await self._db.fetchall(
            "SELECT * FROM automod_rules WHERE guild_id = ?",
            guild_id,
        )
        return [self._row_to_rule(row) for row in rows]

    async def delete_rule(self, guild_id: int, rule_type: str) -> None:
        await self._db.execute(
            "DELETE FROM automod_rules WHERE guild_id = ? AND rule_type = ?",
            guild_id,
            rule_type,
        )


class AuditLogRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    async def add_entry(
        self,
        guild_id: int,
        action: str,
        actor_id: int,
        *,
        target_id: Optional[int] = None,
        context: Optional[str] = None,
    ) -> None:
        await self._db.execute(
            """
            INSERT INTO audit_logs (guild_id, action, actor_id, target_id, context)
            VALUES (?, ?, ?, ?, ?)
            """,
            guild_id,
            action,
            actor_id,
            target_id,
            context,
        )

    async def recent_entries(self, guild_id: int, limit: int = 10, action_prefix: Optional[str] = None) -> list[dict[str, Any]]:
        if action_prefix:
            rows = await self._db.fetchall(
                """
                SELECT * FROM audit_logs
                WHERE guild_id = ? AND action LIKE ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                guild_id,
                f"{action_prefix}%",
                limit,
            )
        else:
            rows = await self._db.fetchall(
                """
                SELECT * FROM audit_logs
                WHERE guild_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                guild_id,
                limit,
            )
        return [dict(row) for row in rows]

    async def action_summary(self, guild_id: int, limit: int = 10, since: Optional[str] = None) -> list[tuple[str, int]]:
        if since:
            rows = await self._db.fetchall(
                """
                SELECT action, COUNT(*) AS total
                FROM audit_logs
                WHERE guild_id = ? AND datetime(created_at) >= datetime(?)
                GROUP BY action
                ORDER BY total DESC
                LIMIT ?
                """,
                guild_id,
                since,
                limit,
            )
        else:
            rows = await self._db.fetchall(
                """
                SELECT action, COUNT(*) AS total
                FROM audit_logs
                WHERE guild_id = ?
                GROUP BY action
                ORDER BY total DESC
                LIMIT ?
                """,
                guild_id,
                limit,
            )
        return [(str(row["action"]), int(row["total"])) for row in rows]

    async def actor_summary(self, guild_id: int, limit: int = 5, since: Optional[str] = None) -> list[tuple[int, int]]:
        if since:
            rows = await self._db.fetchall(
                """
                SELECT actor_id, COUNT(*) AS total
                FROM audit_logs
                WHERE guild_id = ? AND actor_id IS NOT NULL AND datetime(created_at) >= datetime(?)
                GROUP BY actor_id
                ORDER BY total DESC
                LIMIT ?
                """,
                guild_id,
                since,
                limit,
            )
        else:
            rows = await self._db.fetchall(
                """
                SELECT actor_id, COUNT(*) AS total
                FROM audit_logs
                WHERE guild_id = ? AND actor_id IS NOT NULL
                GROUP BY actor_id
                ORDER BY total DESC
                LIMIT ?
                """,
                guild_id,
                limit,
            )
        return [(int(row["actor_id"]), int(row["total"])) for row in rows]


@dataclass(slots=True)
class LevelProfileRecord:
    guild_id: int
    user_id: int
    xp: int
    level: int
    last_message_at: Optional[str]
    created_at: str
    updated_at: str


@dataclass(slots=True)
class LevelProgress:
    profile: LevelProfileRecord
    xp_into_level: int
    xp_for_next_level: int
    leveled_up: bool

    @property
    def xp_remaining(self) -> int:
        return max(self.xp_for_next_level - self.xp_into_level, 0)


@dataclass(slots=True)
class LevelReward:
    guild_id: int
    level: int
    role_id: int


class LevelRepository:
    DEFAULT_COOLDOWN_SECONDS = 60

    def __init__(self, db: Database) -> None:
        self._db = db

    def _row_to_profile(self, row: Any) -> LevelProfileRecord:
        return LevelProfileRecord(
            guild_id=int(row["guild_id"]),
            user_id=int(row["user_id"]),
            xp=int(row["xp"] or 0),
            level=int(row["level"] or 0),
            last_message_at=row["last_message_at"],
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
        )

    def _xp_to_next_level(self, level: int) -> int:
        return 5 * (level ** 2) + 50 * level + 100

    def _calculate_progress(self, xp_total: int) -> tuple[int, int, int]:
        level = 0
        remaining = xp_total
        while True:
            threshold = self._xp_to_next_level(level)
            if remaining < threshold:
                return level, remaining, threshold
            remaining -= threshold
            level += 1

    async def get_profile(self, guild_id: int, user_id: int) -> LevelProfileRecord:
        row = await self._db.fetchone(
            "SELECT * FROM level_profiles WHERE guild_id = ? AND user_id = ?",
            guild_id,
            user_id,
        )
        if row is None:
            await self._db.execute(
                """
                INSERT INTO level_profiles (guild_id, user_id)
                VALUES (?, ?)
                """,
                guild_id,
                user_id,
            )
            row = await self._db.fetchone(
                "SELECT * FROM level_profiles WHERE guild_id = ? AND user_id = ?",
                guild_id,
                user_id,
            )
            assert row is not None
        return self._row_to_profile(row)

    async def get_progress(self, guild_id: int, user_id: int) -> LevelProgress:
        profile = await self.get_profile(guild_id, user_id)
        level, xp_into_level, xp_for_next_level = self._calculate_progress(profile.xp)
        if level != profile.level:
            profile = await self._update_level(guild_id, user_id, profile, level)
        return LevelProgress(profile, xp_into_level, xp_for_next_level, False)

    async def _update_level(
        self,
        guild_id: int,
        user_id: int,
        profile: LevelProfileRecord,
        level: int,
    ) -> LevelProfileRecord:
        await self._db.execute(
            """
            UPDATE level_profiles
            SET level = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE guild_id = ? AND user_id = ?
            """,
            level,
            guild_id,
            user_id,
        )
        row = await self._db.fetchone(
            "SELECT * FROM level_profiles WHERE guild_id = ? AND user_id = ?",
            guild_id,
            user_id,
        )
        assert row is not None
        return self._row_to_profile(row)

    async def add_xp(
        self,
        guild_id: int,
        user_id: int,
        amount: int,
        *,
        now: Optional[datetime] = None,
        cooldown_seconds: Optional[int] = None,
    ) -> LevelProgress:
        if amount <= 0:
            return await self.get_progress(guild_id, user_id)

        profile = await self.get_profile(guild_id, user_id)
        now = now or datetime.now(timezone.utc)
        cooldown = cooldown_seconds or self.DEFAULT_COOLDOWN_SECONDS

        if profile.last_message_at:
            try:
                last = datetime.fromisoformat(profile.last_message_at)
            except ValueError:
                last = None
            if last and now - last < timedelta(seconds=cooldown):
                level, xp_into_level, xp_for_next_level = self._calculate_progress(profile.xp)
                return LevelProgress(profile, xp_into_level, xp_for_next_level, False)

        new_xp = profile.xp + amount
        new_level, xp_into_level, xp_for_next_level = self._calculate_progress(new_xp)
        leveled_up = new_level > profile.level

        await self._db.execute(
            """
            INSERT INTO level_profiles (guild_id, user_id, xp, level, last_message_at, updated_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(guild_id, user_id) DO UPDATE SET
                xp = excluded.xp,
                level = excluded.level,
                last_message_at = excluded.last_message_at,
                updated_at = CURRENT_TIMESTAMP
            """,
            guild_id,
            user_id,
            new_xp,
            new_level,
            now.isoformat(),
        )
        row = await self._db.fetchone(
            "SELECT * FROM level_profiles WHERE guild_id = ? AND user_id = ?",
            guild_id,
            user_id,
        )
        assert row is not None
        updated_profile = self._row_to_profile(row)
        return LevelProgress(updated_profile, xp_into_level, xp_for_next_level, leveled_up)

    async def list_leaderboard(self, guild_id: int, limit: int = 10) -> list[LevelProfileRecord]:
        rows = await self._db.fetchall(
            """
            SELECT * FROM level_profiles
            WHERE guild_id = ?
            ORDER BY level DESC, xp DESC
            LIMIT ?
            """,
            guild_id,
            limit,
        )
        return [self._row_to_profile(row) for row in rows]

    async def list_profiles_with_min_level(self, guild_id: int, min_level: int) -> list[LevelProfileRecord]:
        rows = await self._db.fetchall(
            """
            SELECT * FROM level_profiles
            WHERE guild_id = ? AND level >= ?
            ORDER BY level DESC, xp DESC
            """,
            guild_id,
            min_level,
        )
        return [self._row_to_profile(row) for row in rows]

    async def set_reward(self, guild_id: int, level: int, role_id: int) -> LevelReward:
        await self._db.execute(
            """
            INSERT INTO level_rewards (guild_id, level, role_id)
            VALUES (?, ?, ?)
            ON CONFLICT(guild_id, level) DO UPDATE SET role_id = excluded.role_id
            """,
            guild_id,
            level,
            role_id,
        )
        row = await self._db.fetchone(
            "SELECT * FROM level_rewards WHERE guild_id = ? AND level = ?",
            guild_id,
            level,
        )
        assert row is not None
        return LevelReward(guild_id=guild_id, level=int(row["level"]), role_id=int(row["role_id"]))

    async def remove_reward(self, guild_id: int, level: int) -> bool:
        row = await self._db.fetchone(
            "SELECT id FROM level_rewards WHERE guild_id = ? AND level = ?",
            guild_id,
            level,
        )
        if row is None:
            return False
        await self._db.execute(
            "DELETE FROM level_rewards WHERE guild_id = ? AND level = ?",
            guild_id,
            level,
        )
        return True

    async def list_rewards(self, guild_id: int) -> list[LevelReward]:
        rows = await self._db.fetchall(
            "SELECT * FROM level_rewards WHERE guild_id = ? ORDER BY level",
            guild_id,
        )
        return [LevelReward(guild_id=guild_id, level=int(row["level"]), role_id=int(row["role_id"])) for row in rows]

    async def get_reward_for_level(self, guild_id: int, level: int) -> Optional[LevelReward]:
        row = await self._db.fetchone(
            "SELECT * FROM level_rewards WHERE guild_id = ? AND level = ?",
            guild_id,
            level,
        )
        if row is None:
            return None
        return LevelReward(guild_id=guild_id, level=int(row["level"]), role_id=int(row["role_id"]))


@dataclass(slots=True)
class ScheduledAnnouncement:
    id: int
    guild_id: int
    channel_id: int
    author_id: int
    content: Optional[str]
    embed_title: Optional[str]
    embed_description: Optional[str]
    mention_role_id: Optional[int]
    image_url: Optional[str]
    scheduled_at: str
    status: str
    created_at: str
    delivered_at: Optional[str]


class AnnouncementRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def _row_to_announcement(self, row: Any) -> ScheduledAnnouncement:
        return ScheduledAnnouncement(
            id=int(row["id"]),
            guild_id=int(row["guild_id"]),
            channel_id=int(row["channel_id"]),
            author_id=int(row["author_id"]),
            content=row["content"],
            embed_title=row["embed_title"],
            embed_description=row["embed_description"],
            mention_role_id=row["mention_role_id"],
            image_url=row["image_url"],
            scheduled_at=str(row["scheduled_at"]),
            status=str(row["status"]),
            created_at=str(row["created_at"]),
            delivered_at=row["delivered_at"],
        )

    async def create(
        self,
        guild_id: int,
        channel_id: int,
        author_id: int,
        *,
        content: Optional[str],
        embed_title: Optional[str],
        embed_description: Optional[str],
        mention_role_id: Optional[int],
        image_url: Optional[str],
        scheduled_at: str,
    ) -> ScheduledAnnouncement:
        await self._db.execute(
            """
            INSERT INTO scheduled_announcements (
                guild_id,
                channel_id,
                author_id,
                content,
                embed_title,
                embed_description,
                mention_role_id,
                image_url,
                scheduled_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            guild_id,
            channel_id,
            author_id,
            content,
            embed_title,
            embed_description,
            mention_role_id,
            image_url,
            scheduled_at,
        )
        row = await self._db.fetchone(
            "SELECT * FROM scheduled_announcements WHERE id = last_insert_rowid()",
        )
        if row is None:
            raise RuntimeError("Gagal membuat jadwal pengumuman")
        return self._row_to_announcement(row)

    async def get(self, announcement_id: int) -> Optional[ScheduledAnnouncement]:
        row = await self._db.fetchone(
            "SELECT * FROM scheduled_announcements WHERE id = ?",
            announcement_id,
        )
        return None if row is None else self._row_to_announcement(row)

    async def list_pending(self, guild_id: int) -> list[ScheduledAnnouncement]:
        rows = await self._db.fetchall(
            """
            SELECT * FROM scheduled_announcements
            WHERE guild_id = ? AND status = 'pending'
            ORDER BY scheduled_at ASC
            """,
            guild_id,
        )
        return [self._row_to_announcement(row) for row in rows]

    async def list_pending_all(self) -> list[ScheduledAnnouncement]:
        rows = await self._db.fetchall(
            """
            SELECT * FROM scheduled_announcements
            WHERE status = 'pending'
            ORDER BY scheduled_at ASC
            """,
        )
        return [self._row_to_announcement(row) for row in rows]

    async def list_due(self, now_iso: str) -> list[ScheduledAnnouncement]:
        rows = await self._db.fetchall(
            """
            SELECT * FROM scheduled_announcements
            WHERE status = 'pending' AND scheduled_at <= ?
            ORDER BY scheduled_at ASC
            """,
            now_iso,
        )
        return [self._row_to_announcement(row) for row in rows]

    async def mark_sent(self, announcement_id: int) -> None:
        await self._db.execute(
            """
            UPDATE scheduled_announcements
            SET status = 'sent',
                delivered_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            announcement_id,
        )

    async def cancel(self, announcement_id: int) -> bool:
        row = await self._db.fetchone(
            """
            SELECT status FROM scheduled_announcements
            WHERE id = ?
            """,
            announcement_id,
        )
        if row is None or row["status"] != "pending":
            return False
        await self._db.execute(
            """
            UPDATE scheduled_announcements
            SET status = 'cancelled',
                delivered_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            announcement_id,
        )
        return True
