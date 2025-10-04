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
    CREATE TABLE IF NOT EXISTS couple_profiles (
        couple_id INTEGER PRIMARY KEY,
        title TEXT,
        theme_color TEXT,
        love_song TEXT,
        bio TEXT,
        current_mood TEXT,
        last_checkin_date TEXT,
        checkin_streak INTEGER DEFAULT 0,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (couple_id) REFERENCES couples(id) ON DELETE CASCADE
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS couple_memories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        couple_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        description TEXT,
        created_by INTEGER NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (couple_id) REFERENCES couples(id) ON DELETE CASCADE
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS couple_checkins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        couple_id INTEGER NOT NULL,
        checkin_date TEXT NOT NULL,
        member_one_checked INTEGER DEFAULT 0,
        member_two_checked INTEGER DEFAULT 0,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE (couple_id, checkin_date),
        FOREIGN KEY (couple_id) REFERENCES couples(id) ON DELETE CASCADE
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS couple_milestones (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        couple_id INTEGER NOT NULL,
        milestone_key TEXT NOT NULL,
        achieved_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE (couple_id, milestone_key),
        FOREIGN KEY (couple_id) REFERENCES couples(id) ON DELETE CASCADE
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS couple_gifts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        couple_id INTEGER NOT NULL,
        gift_key TEXT NOT NULL,
        given_by INTEGER NOT NULL,
        message TEXT,
        love_points_awarded INTEGER NOT NULL,
        cost INTEGER NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (couple_id) REFERENCES couples(id) ON DELETE CASCADE
    );
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
