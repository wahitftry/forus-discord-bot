from __future__ import annotations

from typing import Sequence

from .core import Database


CREATE_TABLE_QUERIES: Sequence[str] = (
    """
    CREATE TABLE IF NOT EXISTS guild_settings (
        guild_id INTEGER PRIMARY KEY,
        welcome_channel_id INTEGER,
        goodbye_channel_id INTEGER,
        log_channel_id INTEGER,
        autorole_id INTEGER,
        timezone TEXT DEFAULT 'Asia/Jakarta',
        ticket_category_id INTEGER,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS warns (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        guild_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        moderator_id INTEGER NOT NULL,
        reason TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS economy (
        guild_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        balance INTEGER DEFAULT 0,
        last_daily TEXT,
        last_work TEXT,
        PRIMARY KEY (guild_id, user_id)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS inventory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        guild_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        item_name TEXT NOT NULL,
        quantity INTEGER DEFAULT 0
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS shop_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        guild_id INTEGER NOT NULL,
        item_name TEXT NOT NULL,
        price INTEGER NOT NULL,
        description TEXT,
        role_reward_id INTEGER
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS reminders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        guild_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        message TEXT NOT NULL,
        remind_at TEXT NOT NULL,
        channel_id INTEGER,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS tickets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        guild_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        channel_id INTEGER NOT NULL,
        status TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        closed_at TEXT
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS couples (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        guild_id INTEGER NOT NULL,
        member_one_id INTEGER NOT NULL,
        member_two_id INTEGER NOT NULL,
        initiator_id INTEGER NOT NULL,
        pending_target_id INTEGER NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending',
        proposal_message TEXT,
        anniversary TEXT,
        love_points INTEGER DEFAULT 0,
        last_affection_one TEXT,
        last_affection_two TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        ended_at TEXT,
        ended_by INTEGER,
        CHECK (member_one_id < member_two_id)
    );
    """,
    """
    CREATE UNIQUE INDEX IF NOT EXISTS idx_couples_member_one
    ON couples (guild_id, member_one_id)
    WHERE status IN ('pending', 'active');
    """,
    """
    CREATE UNIQUE INDEX IF NOT EXISTS idx_couples_member_two
    ON couples (guild_id, member_two_id)
    WHERE status IN ('pending', 'active');
    """,
    """
    CREATE UNIQUE INDEX IF NOT EXISTS idx_couples_pair_active
    ON couples (guild_id, member_one_id, member_two_id)
    WHERE status IN ('pending', 'active');
    """,
    """
    CREATE TABLE IF NOT EXISTS audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        guild_id INTEGER NOT NULL,
        action TEXT NOT NULL,
        actor_id INTEGER NOT NULL,
        target_id INTEGER,
        context TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS automod_rules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        guild_id INTEGER NOT NULL,
        rule_type TEXT NOT NULL,
        value_json TEXT NOT NULL,
        is_active INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    """
)


async def run_migrations() -> None:
    db = Database.instance()
    for query in CREATE_TABLE_QUERIES:
        await db.execute(query)
