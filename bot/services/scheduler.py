from __future__ import annotations

from typing import Any, Awaitable, Callable

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

    def schedule_once(self, job_id: str, run_time, func: Callable[..., Awaitable[Any]], *args: Any) -> None:
        self._scheduler.add_job(
            func,
            "date",
            run_date=run_time,
            args=list(args),
            id=job_id,
            replace_existing=True,
        )

    def schedule_reminder(self, reminder_id: int, run_time, func: Callable[[int], Awaitable[None]]) -> None:
        self.schedule_once(f"reminder-{reminder_id}", run_time, func, reminder_id)

    def has_job(self, job_id: str) -> bool:
        return self._scheduler.get_job(job_id) is not None

    def cancel(self, job_id: str) -> None:
        job = self._scheduler.get_job(job_id)
        if job:
            job.remove()
