from datetime import datetime, timezone
from pathlib import Path

import pytest
import pytest_asyncio

from bot.database.core import Database
from bot.database import migrations
from bot.database.repositories import CoupleRepository, EconomyRepository, GuildSettingsRepository, ReminderRepository


@pytest_asyncio.fixture()
async def temp_db(tmp_path: Path):
    db_path = tmp_path / "test.db"
    url = f"sqlite+aiosqlite:///{db_path}"
    db = await Database.initialize(url)
    await migrations.run_migrations()
    yield db
    await db.close()


@pytest.mark.asyncio()
async def test_guild_settings_upsert(temp_db):
    repo = GuildSettingsRepository(temp_db)
    await repo.upsert(123, welcome_channel_id=456)
    settings = await repo.get(123)
    assert settings is not None
    assert settings.welcome_channel_id == 456
    await repo.upsert(123, goodbye_channel_id=789)
    settings = await repo.get(123)
    assert settings is not None
    assert settings.goodbye_channel_id == 789


@pytest.mark.asyncio()
async def test_economy_balance(temp_db):
    repo = EconomyRepository(temp_db)
    balance = await repo.get_balance(1, 1)
    assert balance == 0
    new_balance = await repo.update_balance(1, 1, 100)
    assert new_balance == 100
    leaderboard = await repo.top_balances(1)
    assert leaderboard == [(1, 100)]


@pytest.mark.asyncio()
async def test_economy_daily_timestamp_upsert(temp_db):
    repo = EconomyRepository(temp_db)
    await repo.set_daily_timestamp(99, 5, "2025-01-02T03:04:05+00:00")
    timestamp = await repo.get_daily_timestamp(99, 5)
    assert timestamp == "2025-01-02T03:04:05+00:00"


@pytest.mark.asyncio()
async def test_reminder_crud(temp_db):
    repo = ReminderRepository(temp_db)
    reminder_id = await repo.create(1, 2, "Halo", "2025-01-01T00:00:00+00:00", None)
    reminders = await repo.list_for_user(1, 2)
    assert any(r["id"] == reminder_id for r in reminders)
    await repo.delete(reminder_id)
    reminders = await repo.list_for_user(1, 2)
    assert not reminders


@pytest.mark.asyncio()
async def test_couple_repository_lifecycle(temp_db):
    repo = CoupleRepository(temp_db)
    guild_id = 321
    user_a = 1001
    user_b = 2002

    proposal = await repo.create_proposal(guild_id, user_a, user_b, "Selalu bersamamu")
    assert proposal.status == "pending"
    assert await repo.user_has_active_or_pending(guild_id, user_a)
    assert await repo.user_has_active_or_pending(guild_id, user_b)

    pending = await repo.get_pending_for_target(guild_id, user_b)
    assert pending is not None and pending.id == proposal.id

    accepted = await repo.accept_proposal(proposal.id, "2024-10-03")
    assert accepted is not None
    assert accepted.status == "active"
    assert accepted.anniversary == "2024-10-03"

    boosted = await repo.add_love_points(accepted.id, 25)
    assert boosted is not None and boosted.love_points >= 25

    now_iso = datetime.now(timezone.utc).isoformat()
    affection_updated = await repo.update_last_affection(boosted, user_a, now_iso)
    assert affection_updated is not None
    assert affection_updated.last_affection_one == now_iso or affection_updated.last_affection_two == now_iso

    leaderboard = await repo.list_leaderboard(guild_id)
    assert any(entry.id == accepted.id for entry in leaderboard)

    ended = await repo.end_relationship(accepted.id, user_a)
    assert ended is not None and ended.status == "ended"
    assert not await repo.user_has_active_or_pending(guild_id, user_a)
    assert not await repo.user_has_active_or_pending(guild_id, user_b)

    reproposal = await repo.create_proposal(guild_id, user_a, user_b, None)
    assert reproposal.status == "pending"


@pytest.mark.asyncio()
async def test_couple_reject_clears_pending(temp_db):
    repo = CoupleRepository(temp_db)
    guild_id = 654
    initiator = 1
    target = 2

    proposal = await repo.create_proposal(guild_id, initiator, target, None)
    assert proposal.status == "pending"

    await repo.reject_proposal(proposal.id, target)
    assert not await repo.user_has_active_or_pending(guild_id, initiator)
    assert not await repo.user_has_active_or_pending(guild_id, target)
    assert await repo.get_pending_for_target(guild_id, target) is None
