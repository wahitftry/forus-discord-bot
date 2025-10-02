from __future__ import annotations

from typing import Awaitable, Callable

from apscheduler.schedulers.asyncio import AsyncIOScheduler


class Scheduler:
    """Wrapper sederhana untuk APScheduler."""

    def __init__(self) -> None:
        self._scheduler = AsyncIOScheduler()

    def start(self) -> None:
        if not self._scheduler.running:
            self._scheduler.start()

    def shutdown(self, wait: bool = True) -> None:
        if self._scheduler.running:
            self._scheduler.shutdown(wait=wait)

    def schedule_reminder(self, reminder_id: int, run_time, func: Callable[[int], Awaitable[None]]) -> None:
        self._scheduler.add_job(func, "date", run_date=run_time, args=[reminder_id], id=f"reminder-{reminder_id}")

    def has_job(self, job_id: str) -> bool:
        return self._scheduler.get_job(job_id) is not None
