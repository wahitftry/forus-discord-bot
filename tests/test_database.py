from pathlib import Path

import pytest
import pytest_asyncio

from bot.database.core import Database
from bot.database import migrations
from bot.database.repositories import EconomyRepository, GuildSettingsRepository, ReminderRepository


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
