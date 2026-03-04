"""
Unit tests for async scheduler - TDD RED phase.

Tests cover:
- AsyncIOScheduler initialization
- Job scheduling with cron patterns
- Parallel data collection
- Job execution
- Error handling

Following TDD RED-GREEN-REFACTOR cycle.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio


class TestAsyncSchedulerInitialization:
    """Test AsyncScheduler initialization - RED phase."""

    def test_scheduler_initialization(self):
        """AsyncScheduler should initialize with default settings."""
        from gpt_bitcoin.application.scheduler import AsyncScheduler

        scheduler = AsyncScheduler()

        assert scheduler is not None
        assert scheduler._jobs is not None
        assert scheduler._running is False

    def test_scheduler_with_custom_settings(self):
        """AsyncScheduler should accept custom settings."""
        from gpt_bitcoin.application.scheduler import AsyncScheduler
        from gpt_bitcoin.config.settings import Settings

        settings = MagicMock()
        settings.schedule_times = ["00:01", "08:01", "16:01"]

        scheduler = AsyncScheduler(settings=settings)

        assert scheduler._settings is not None


class TestAsyncSchedulerJobScheduling:
    """Test AsyncScheduler job scheduling - RED phase."""

    @pytest.fixture
    def scheduler(self):
        """Create AsyncScheduler instance."""
        from gpt_bitcoin.application.scheduler import AsyncScheduler
        return AsyncScheduler()

    def test_add_job_with_cron_pattern(self, scheduler):
        """AsyncScheduler should add job with cron pattern."""
        async def dummy_job():
            pass

        scheduler.add_job(dummy_job, cron_expression="0 8 * * *")

        assert len(scheduler._jobs) == 1

    def test_add_job_with_interval(self, scheduler):
        """AsyncScheduler should add job with interval."""
        async def dummy_job():
            pass

        scheduler.add_job(dummy_job, interval_seconds=3600)

        assert len(scheduler._jobs) == 1

    def test_add_multiple_jobs(self, scheduler):
        """AsyncScheduler should handle multiple jobs."""
        async def job1():
            pass

        async def job2():
            pass

        scheduler.add_job(job1, interval_seconds=3600)
        scheduler.add_job(job2, interval_seconds=7200)

        assert len(scheduler._jobs) == 2


class TestAsyncSchedulerStartStop:
    """Test AsyncScheduler start and stop - RED phase."""

    @pytest.fixture
    def scheduler(self):
        """Create AsyncScheduler instance."""
        from gpt_bitcoin.application.scheduler import AsyncScheduler
        return AsyncScheduler()

    @pytest.mark.asyncio
    async def test_start_scheduler(self, scheduler):
        """AsyncScheduler should start and set running flag."""
        await scheduler.start()

        assert scheduler._running is True

        await scheduler.stop()

    @pytest.mark.asyncio
    async def test_stop_scheduler(self, scheduler):
        """AsyncScheduler should stop and clear running flag."""
        await scheduler.start()
        await scheduler.stop()

        assert scheduler._running is False

    @pytest.mark.asyncio
    async def test_start_when_already_running(self, scheduler):
        """AsyncScheduler should not start if already running."""
        await scheduler.start()
        first_task = scheduler._task

        await scheduler.start()  # Should be no-op

        assert scheduler._task is first_task

        await scheduler.stop()


class TestAsyncSchedulerJobExecution:
    """Test AsyncScheduler job execution - RED phase."""

    @pytest.fixture
    def scheduler(self):
        """Create AsyncScheduler instance."""
        from gpt_bitcoin.application.scheduler import AsyncScheduler
        return AsyncScheduler()

    @pytest.mark.asyncio
    async def test_execute_job_calls_coroutine(self, scheduler):
        """AsyncScheduler should execute job coroutine."""
        call_count = 0

        async def counting_job():
            nonlocal call_count
            call_count += 1

        # Run immediately for testing
        scheduler.add_job(counting_job, interval_seconds=0.1, run_immediately=True)

        await scheduler.start()
        await asyncio.sleep(0.15)  # Allow job to execute
        await scheduler.stop()

        assert call_count >= 1

    @pytest.mark.asyncio
    async def test_job_error_does_not_stop_scheduler(self, scheduler):
        """AsyncScheduler should continue after job error."""
        call_count = 0

        async def failing_job():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("Job failed")

        # Run immediately for testing, very short interval
        scheduler.add_job(failing_job, interval_seconds=0.05, run_immediately=True)

        await scheduler.start()
        # Verify that error handling doesn't crash scheduler
        # First run happens immediately and fails
        await asyncio.sleep(0.2)  # Wait for first run to complete

        # Manually trigger another check to verify scheduler still works
        await scheduler._check_and_execute_jobs()

        await scheduler.stop()

        # Should have executed at least twice despite error
        assert call_count >= 2


class TestParallelDataCollection:
    """Test parallel data collection - RED phase."""

    @pytest.mark.asyncio
    async def test_fetch_all_data_parallel(self):
        """Should fetch news, chart, and fear_greed in parallel."""
        from gpt_bitcoin.application.scheduler import fetch_all_data_parallel

        news_called = False
        chart_called = False
        fear_greed_called = False

        async def mock_news():
            nonlocal news_called
            news_called = True
            await asyncio.sleep(0.1)
            return {"news": "data"}

        async def mock_chart():
            nonlocal chart_called
            chart_called = True
            await asyncio.sleep(0.1)
            return {"chart": "data"}

        async def mock_fear_greed():
            nonlocal fear_greed_called
            fear_greed_called = True
            await asyncio.sleep(0.1)
            return {"fear_greed": 50}

        # Run in parallel
        start_time = asyncio.get_event_loop().time()
        results = await fetch_all_data_parallel(
            fetch_news=mock_news,
            fetch_chart=mock_chart,
            fetch_fear_greed=mock_fear_greed,
        )
        elapsed = asyncio.get_event_loop().time() - start_time

        # All should be called
        assert news_called is True
        assert chart_called is True
        assert fear_greed_called is True

        # Should complete in ~0.1s (parallel) not ~0.3s (sequential)
        assert elapsed < 0.25

        # Should return all results
        assert "news" in results
        assert "chart" in results
        assert "fear_greed" in results

    @pytest.mark.asyncio
    async def test_fetch_all_data_handles_partial_failure(self):
        """Should handle partial failures in parallel fetch."""
        from gpt_bitcoin.application.scheduler import fetch_all_data_parallel

        async def mock_news():
            return {"news": "data"}

        async def mock_chart():
            raise ValueError("Chart API failed")

        async def mock_fear_greed():
            return {"fear_greed": 50}

        results = await fetch_all_data_parallel(
            fetch_news=mock_news,
            fetch_chart=mock_chart,
            fetch_fear_greed=mock_fear_greed,
        )

        # Should have results for successful fetches
        assert results["news"] == {"news": "data"}
        assert results["fear_greed"] == {"fear_greed": 50}
        # Failed fetch should be None
        assert results.get("chart") is None


class TestSchedulerFromSettings:
    """Test scheduler configuration from settings - RED phase."""

    def test_scheduler_uses_schedule_times(self):
        """AsyncScheduler should use schedule_times from settings."""
        from gpt_bitcoin.application.scheduler import AsyncScheduler

        settings = MagicMock()
        settings.schedule_times = ["00:01", "08:01", "16:01"]

        scheduler = AsyncScheduler(settings=settings)

        # Should parse schedule times
        assert len(scheduler._schedule_times) == 3

    def test_scheduler_default_schedule(self):
        """AsyncScheduler should have default schedule."""
        from gpt_bitcoin.application.scheduler import AsyncScheduler

        scheduler = AsyncScheduler()

        # Should have default schedule times
        assert len(scheduler._schedule_times) > 0
