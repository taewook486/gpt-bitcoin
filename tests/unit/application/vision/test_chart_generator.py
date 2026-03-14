"""
Unit tests for ChartGenerator.

Tests candlestick chart generation with technical indicators.
"""

from datetime import datetime, timedelta
from pathlib import Path

import pytest

from gpt_bitcoin.application.vision.chart_generator import ChartGenerator
from gpt_bitcoin.domain.models.cryptocurrency import Cryptocurrency


@pytest.fixture
def output_dir(tmp_path: Path) -> Path:
    """Create temporary output directory for charts."""
    chart_dir = tmp_path / "charts"
    chart_dir.mkdir(parents=True, exist_ok=True)
    return chart_dir


@pytest.fixture
def chart_generator(output_dir: Path) -> ChartGenerator:
    """Create ChartGenerator instance with temporary output directory."""
    return ChartGenerator(output_dir=output_dir)


@pytest.fixture
def sample_ohlcv_data() -> list[dict]:
    """Create sample OHLCV data for testing (100 candles)."""
    data = []
    base_time = int(datetime.now().timestamp())
    base_price = 70_000_000  # 70 million KRW

    for i in range(100):
        timestamp = base_time - (99 - i) * 3600  # Hourly candles
        variation = (i % 10 - 5) * 100_000  # Price variation
        open_price = base_price + variation
        close_price = open_price + ((i % 7) - 3) * 50_000
        high_price = max(open_price, close_price) + abs(i % 5) * 20_000
        low_price = min(open_price, close_price) - abs(i % 4) * 15_000
        volume = 1000 + (i % 20) * 100

        data.append(
            {
                "timestamp": timestamp,
                "open": open_price,
                "high": high_price,
                "low": low_price,
                "close": close_price,
                "volume": volume,
            }
        )

    return data


class TestChartGenerator:
    """Test suite for ChartGenerator."""

    @pytest.mark.asyncio
    async def test_generate_chart_success(
        self,
        chart_generator: ChartGenerator,
        sample_ohlcv_data: list[dict],
    ):
        """Test successful chart generation."""
        chart_path = await chart_generator.generate_chart(
            coin=Cryptocurrency.BTC,
            ohlcv_data=sample_ohlcv_data,
            period="1h",
            days=1,
        )

        # Verify chart was created
        assert chart_path.exists()
        assert chart_path.suffix == ".png"
        assert chart_path.stat().st_size > 0

        # Verify filename format
        assert "BTC" in chart_path.name
        assert "1h" in chart_path.name

    @pytest.mark.asyncio
    async def test_generate_chart_insufficient_data(
        self,
        chart_generator: ChartGenerator,
    ):
        """Test chart generation with insufficient data."""
        # Create minimal data (less than 20 candles)
        minimal_data = [
            {
                "timestamp": int(datetime.now().timestamp()) - i * 3600,
                "open": 70_000_000,
                "high": 70_100_000,
                "low": 69_900_000,
                "close": 70_050_000,
                "volume": 1000,
            }
            for i in range(10)
        ]

        with pytest.raises(ValueError, match="Insufficient data points"):
            await chart_generator.generate_chart(
                coin=Cryptocurrency.BTC,
                ohlcv_data=minimal_data,
                period="1h",
                days=1,
            )

    @pytest.mark.asyncio
    async def test_generate_chart_missing_columns(
        self,
        chart_generator: ChartGenerator,
    ):
        """Test chart generation with missing required columns."""
        invalid_data = [
            {"timestamp": int(datetime.now().timestamp()) - i * 3600} for i in range(30)
        ]

        with pytest.raises(ValueError, match="Missing required columns"):
            await chart_generator.generate_chart(
                coin=Cryptocurrency.BTC,
                ohlcv_data=invalid_data,
                period="1h",
                days=1,
            )

    @pytest.mark.asyncio
    async def test_generate_chart_different_coins(
        self,
        chart_generator: ChartGenerator,
        sample_ohlcv_data: list[dict],
    ):
        """Test chart generation for different cryptocurrencies."""
        for coin in [Cryptocurrency.ETH, Cryptocurrency.SOL]:
            chart_path = await chart_generator.generate_chart(
                coin=coin,
                ohlcv_data=sample_ohlcv_data,
                period="1h",
                days=1,
            )

            assert chart_path.exists()
            assert coin.value in chart_path.name

    @pytest.mark.asyncio
    async def test_generate_chart_different_periods(
        self,
        chart_generator: ChartGenerator,
        sample_ohlcv_data: list[dict],
    ):
        """Test chart generation for different time periods."""
        for period in ["1h", "4h", "1d"]:
            chart_path = await chart_generator.generate_chart(
                coin=Cryptocurrency.BTC,
                ohlcv_data=sample_ohlcv_data,
                period=period,
                days=1,
            )

            assert chart_path.exists()
            assert period in chart_path.name

    @pytest.mark.asyncio
    async def test_generate_chart_datetime_format(
        self,
        chart_generator: ChartGenerator,
    ):
        """Test chart generation with datetime format instead of timestamp."""
        data = [
            {
                "datetime": datetime.now() - timedelta(hours=i),
                "open": 70_000_000,
                "high": 70_100_000,
                "low": 69_900_000,
                "close": 70_050_000,
                "volume": 1000,
            }
            for i in range(30)
        ]

        chart_path = await chart_generator.generate_chart(
            coin=Cryptocurrency.BTC,
            ohlcv_data=data,
            period="1h",
            days=1,
        )

        assert chart_path.exists()

    @pytest.mark.asyncio
    async def test_cleanup_old_charts(
        self,
        chart_generator: ChartGenerator,
        output_dir: Path,
    ):
        """Test cleanup of old chart files."""
        # Create an old chart file
        old_chart = output_dir / "old_chart.png"
        old_chart.write_bytes(b"fake chart data")

        # Set modification time to 25 hours ago
        import os

        old_time = datetime.now() - timedelta(hours=25)
        os.utime(old_chart, (old_time.timestamp(), old_time.timestamp()))

        # Run cleanup
        await chart_generator.cleanup_old_charts(max_age_hours=24)

        # Verify old chart was removed
        assert not old_chart.exists()

    def test_technical_indicators_calculation(
        self,
        chart_generator: ChartGenerator,
    ):
        """Test technical indicator calculations."""
        import pandas as pd

        # Create sample price data
        prices = pd.Series([100, 101, 102, 103, 104, 105, 106, 107, 108, 109])

        # Calculate MACD
        macd = chart_generator._calculate_macd(prices)

        assert "macd" in macd
        assert "signal" in macd
        assert "histogram" in macd

        # Verify MACD calculation
        assert len(macd["macd"]) == len(prices)
        assert len(macd["signal"]) == len(prices)

    def test_chart_generator_initialization(
        self,
        output_dir: Path,
    ):
        """Test ChartGenerator initialization."""
        generator = ChartGenerator(
            output_dir=output_dir,
            ma_short_period=20,
            ma_long_period=60,
        )

        assert generator.output_dir == output_dir
        assert generator.ma_short_period == 20
        assert generator.ma_long_period == 60
