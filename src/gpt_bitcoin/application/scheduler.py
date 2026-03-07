"""
Async scheduler for trading system.

This module provides async-first job scheduling using asyncio,
replacing the synchronous schedule library with native async support.

Features:
- AsyncIO-based scheduling
- Cron expression support
- Interval-based scheduling
- Parallel data collection
- Error handling with continuation

@MX:NOTE: This scheduler replaces the legacy schedule-based implementation
with native async/await support for better resource utilization.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, Coroutine

from gpt_bitcoin.config.settings import Settings, get_settings
from gpt_bitcoin.infrastructure.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ScheduledJob:
    """
    Represents a scheduled job.

    @MX:NOTE: Stores job configuration and execution state.
    """

    func: Callable[[], Coroutine[Any, Any, None]]
    interval_seconds: float | None = None
    cron_expression: str | None = None
    last_run: datetime | None = None
    next_run: datetime | None = None
    error_count: int = 0


class AsyncScheduler:
    """
    Async-first job scheduler using asyncio.

    Provides scheduling capabilities with:
    - Interval-based scheduling
    - Cron expression support (basic)
    - Error handling with job continuation
    - Parallel job execution

    Example:
        ```python
        scheduler = AsyncScheduler(settings)

        async def trading_job():
            # Fetch data in parallel
            data = await fetch_all_data_parallel(...)
            # Execute trading logic

        scheduler.add_job(trading_job, interval_seconds=28800)  # Every 8 hours

        await scheduler.start()
        # ... scheduler runs in background ...
        await scheduler.stop()
        ```
    """

    def __init__(self, settings: Settings | None = None):
        """
        Initialize the scheduler.

        Args:
            settings: Application settings (uses global if not provided)
        """
        self._settings = settings or get_settings()
        self._jobs: list[ScheduledJob] = []
        self._running = False
        self._task: asyncio.Task | None = None
        self._schedule_times: list[str] = self._parse_schedule_times()

        logger.info(
            "AsyncScheduler initialized",
            schedule_times=self._schedule_times,
        )

    def _parse_schedule_times(self) -> list[str]:
        """
        Parse schedule times from settings.

        Returns:
            List of schedule times in HH:MM format
        """
        times = self._settings.schedule_times
        # Validate format
        parsed = []
        for time_str in times:
            try:
                # Validate HH:MM format
                datetime.strptime(time_str, "%H:%M")
                parsed.append(time_str)
            except ValueError:
                logger.warning(
                    "Invalid schedule time format, skipping",
                    time=time_str,
                )
        return parsed

    def add_job(
        self,
        func: Callable[[], Coroutine[Any, Any, None]],
        interval_seconds: float | None = None,
        cron_expression: str | None = None,
        run_immediately: bool = False,
    ) -> None:
        """
        Add a job to the scheduler.

        Args:
            func: Async function to execute
            interval_seconds: Interval between executions (optional)
            cron_expression: Cron expression for scheduling (optional)
            run_immediately: Whether to run job immediately (default: False)

        Note:
            At least one of interval_seconds or cron_expression must be provided.
        """
        job = ScheduledJob(
            func=func,
            interval_seconds=interval_seconds,
            cron_expression=cron_expression,
        )

        # Calculate next run time
        if run_immediately:
            job.next_run = datetime.now()
        elif interval_seconds:
            job.next_run = datetime.now() + timedelta(seconds=interval_seconds)
        elif cron_expression:
            # Basic cron parsing - just use first run time
            job.next_run = self._parse_cron_next_run(cron_expression)

        self._jobs.append(job)

        logger.info(
            "Job added to scheduler",
            interval=interval_seconds,
            cron=cron_expression,
            next_run=job.next_run.isoformat() if job.next_run else None,
        )

    def _parse_cron_next_run(self, cron_expression: str) -> datetime:
        """
        Parse cron expression and calculate next run time.

        This is a simplified cron parser that handles basic patterns.
        For full cron support, use croniter library.

        Args:
            cron_expression: Cron expression (e.g., "0 8 * * *")

        Returns:
            Next run datetime
        """
        # Simplified: just schedule for next occurrence
        # In production, use croniter for full cron support
        parts = cron_expression.split()
        if len(parts) >= 2:
            minute = int(parts[0]) if parts[0] != "*" else 0
            hour = int(parts[1]) if parts[1] != "*" else 0

            now = datetime.now()
            next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

            if next_run <= now:
                next_run += timedelta(days=1)

            return next_run

        # Default: run in 1 hour
        return datetime.now() + timedelta(hours=1)

    async def start(self) -> None:
        """
        Start the scheduler.

        Creates a background task that executes scheduled jobs.
        """
        if self._running:
            logger.warning("Scheduler already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._run_loop())

        logger.info("Scheduler started")

    async def stop(self) -> None:
        """
        Stop the scheduler.

        Cancels the background task and waits for completion.
        """
        if not self._running:
            return

        self._running = False

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

        logger.info("Scheduler stopped")

    async def _run_loop(self) -> None:
        """
        Main scheduler loop.

        Continuously checks for jobs to execute and runs them.
        """
        logger.debug("Scheduler loop started")

        while self._running:
            try:
                await self._check_and_execute_jobs()
                await asyncio.sleep(1.0)  # Check every second
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Scheduler loop error", error=str(e))
                await asyncio.sleep(5.0)  # Back off on error

        logger.debug("Scheduler loop ended")

    async def _check_and_execute_jobs(self) -> None:
        """
        Check for jobs ready to execute and run them.
        """
        now = datetime.now()

        for job in self._jobs:
            if job.next_run and job.next_run <= now:
                # Execute job in background
                asyncio.create_task(self._execute_job(job))

                # Schedule next run
                if job.interval_seconds:
                    job.next_run = now + timedelta(seconds=job.interval_seconds)
                elif job.cron_expression:
                    job.next_run = self._parse_cron_next_run(job.cron_expression)

                job.last_run = now

    async def _execute_job(self, job: ScheduledJob) -> None:
        """
        Execute a single job with error handling.

        Args:
            job: The job to execute
        """
        try:
            await job.func()
            job.error_count = 0  # Reset on success
            logger.debug("Job executed successfully")
        except Exception as e:
            job.error_count += 1
            logger.error(
                "Job execution failed",
                error=str(e),
                error_count=job.error_count,
            )
            # Job continues despite error


async def fetch_all_data_parallel(
    fetch_news: Callable[[], Coroutine[Any, Any, Any]],
    fetch_chart: Callable[[], Coroutine[Any, Any, Any]],
    fetch_fear_greed: Callable[[], Coroutine[Any, Any, Any]],
) -> dict[str, Any]:
    """
    Fetch data from multiple sources in parallel.

    Uses asyncio.gather to fetch news, chart, and fear/greed data
    concurrently for improved performance.

    Args:
        fetch_news: Async function to fetch news data
        fetch_chart: Async function to fetch chart data
        fetch_fear_greed: Async function to fetch fear/greed index

    Returns:
        Dictionary with news, chart, and fear_greed data.
        Failed fetches return None for that key.

    Example:
        ```python
        results = await fetch_all_data_parallel(
            fetch_news=client.get_news,
            fetch_chart=client.get_chart,
            fetch_fear_greed=client.get_fear_greed,
        )
        news = results["news"]
        chart = results["chart"]
        fear_greed = results["fear_greed"]
        ```

    @MX:NOTE: This replaces sequential API calls with parallel execution,
    reducing total fetch time from ~3s to ~1s.
    """
    results: dict[str, Any] = {}

    async def safe_fetch(
        name: str,
        fetch_func: Callable[[], Coroutine[Any, Any, Any]],
    ) -> tuple[str, Any]:
        """Fetch with error handling."""
        try:
            result = await fetch_func()
            return (name, result)
        except Exception as e:
            logger.warning(
                "Parallel fetch failed for source",
                source=name,
                error=str(e),
            )
            return (name, None)

    # Execute all fetches in parallel
    tasks = [
        safe_fetch("news", fetch_news),
        safe_fetch("chart", fetch_chart),
        safe_fetch("fear_greed", fetch_fear_greed),
    ]

    gathered_results = await asyncio.gather(*tasks)

    # Build results dict
    for name, result in gathered_results:
        results[name] = result

    return results
