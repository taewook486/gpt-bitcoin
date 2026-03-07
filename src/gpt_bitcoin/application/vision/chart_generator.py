"""
Chart generator for creating candlestick charts with technical indicators.

This module uses mplfinance to generate professional candlestick charts
with moving averages, volume, and MACD indicators for Vision API analysis.
"""

from __future__ import annotations

import io
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend for server environment
import mplfinance as mpf
import pandas as pd

from gpt_bitcoin.domain.models.cryptocurrency import Cryptocurrency
from gpt_bitcoin.infrastructure.logging import get_logger

logger = get_logger(__name__)


class ChartGenerator:
    """
    Generate candlestick charts with technical indicators for Vision API.

    @MX:NOTE Chart generation uses mplfinance for professional financial charts.
    """

    def __init__(
        self,
        output_dir: Path | str = "./charts",
        ma_short_period: int = 15,
        ma_long_period: int = 50,
    ):
        """
        Initialize chart generator.

        Args:
            output_dir: Directory to save chart images
            ma_short_period: Short moving average period (default: 15 hours)
            ma_long_period: Long moving average period (default: 50 hours)
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.ma_short_period = ma_short_period
        self.ma_long_period = ma_long_period

        logger.info(
            "ChartGenerator initialized",
            output_dir=str(self.output_dir),
            ma_short=ma_short_period,
            ma_long=ma_long_period,
        )

    async def generate_chart(
        self,
        coin: Cryptocurrency,
        ohlcv_data: list[dict[str, Any]],
        period: str = "1h",
        days: int = 1,
    ) -> Path:
        """
        Generate candlestick chart image for Vision API analysis.

        Args:
            coin: Cryptocurrency to generate chart for
            ohlcv_data: List of OHLCV dictionaries with keys:
                - timestamp: Unix timestamp or datetime
                - open: Opening price
                - high: High price
                - low: Low price
                - close: Closing price
                - volume: Trading volume
            period: Time period (1h, 4h, 1d)
            days: Number of days to include in chart

        Returns:
            Path to generated chart image

        Raises:
            ValueError: If data is insufficient
            IOError: If chart generation fails

        @MX:NOTE Generates candlestick chart with MAs and MACD for Vision API.
        """
        logger.info(
            "Generating chart",
            coin=coin.value,
            period=period,
            days=days,
            data_points=len(ohlcv_data),
        )

        # Convert to DataFrame
        df = self._prepare_dataframe(ohlcv_data)

        # Filter to requested time range
        end_time = df.index[-1]
        start_time = end_time - timedelta(days=days)
        df = df[df.index >= start_time]

        if len(df) < 20:
            raise ValueError(
                f"Insufficient data points ({len(df)}) for chart generation. "
                f"Need at least 20 candles."
            )

        # Calculate technical indicators
        df = self._add_technical_indicators(df)

        # Generate chart
        chart_path = self.output_dir / f"{coin.value}_{period}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"

        # Create custom style for Vision API
        mc = mpf.make_marketcolors(
            up='tab:green',
            down='tab:red',
            edge='black',
            wick={'up': 'green', 'down': 'red'},
            volume='in',
        )

        # Configure plot style with simpler approach
        s = mpf.make_mpf_style(
            base_mpf_style='charles',
            marketcolors=mc,
            gridstyle='',
            ypad=0.1,
        )

        # Add MACD indicator
        macd = self._calculate_macd(df['close'])
        df_macd = pd.DataFrame({
            'MACD_12_26_9': macd['macd'],
            'MACDs_12_26_9': macd['signal'],
            'MACDh_12_26_9': macd['histogram'],
        }, index=df.index)

        # Generate chart with all indicators
        fig, axes = mpf.plot(
            df,
            type='candle',
            style=s,
            title=f'{coin.display_name} ({coin.upbit_ticker}) - {period}',
            ylabel='Price (KRW)',
            volume_panel=True,
            mavp=('MA_Short', 'MA_Long'),
            addplot=df_macd,
            savefig=dict(fname=str(chart_path), dpi=150, bbox_inches='tight'),
            returnfig=True,
        )

        # Close figure to free memory
        fig.clear()
        plt.close('all')  # Close all matplotlib figures

        logger.info(
            "Chart generated successfully",
            chart_path=str(chart_path),
            candles=len(df),
            file_size_kb=chart_path.stat().st_size / 1024,
        )

        return chart_path

    def _prepare_dataframe(self, ohlcv_data: list[dict[str, Any]]) -> pd.DataFrame:
        """
        Convert OHLCV data to pandas DataFrame with proper formatting.

        Args:
            ohlcv_data: List of OHLCV dictionaries

        Returns:
            DataFrame with DatetimeIndex and OHLCV columns

        @MX:NOTE Converts raw OHLCV data to mplfinance-compatible DataFrame.
        """
        df = pd.DataFrame(ohlcv_data)

        # Parse timestamp
        if 'timestamp' in df.columns:
            df['datetime'] = pd.to_datetime(df['timestamp'], unit='s')
        elif 'datetime' in df.columns:
            df['datetime'] = pd.to_datetime(df['datetime'])
        else:
            raise ValueError("OHLCV data must contain 'timestamp' or 'datetime' field")

        df.set_index('datetime', inplace=True)
        df.sort_index(inplace=True)

        # Rename columns to mplfinance expected names
        column_mapping = {
            'open': 'Open',
            'high': 'High',
            'low': 'Low',
            'close': 'Close',
            'volume': 'Volume',
        }
        df.rename(columns=column_mapping, inplace=True)

        # Ensure required columns exist
        required = ['Open', 'High', 'Low', 'Close', 'Volume']
        missing = [col for col in required if col not in df.columns]
        if missing:
            raise ValueError(f"Missing required columns: {missing}")

        return df[required]

    def _add_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add technical indicators to DataFrame.

        Args:
            df: OHLCV DataFrame

        Returns:
            DataFrame with MA columns added

        @MX:NOTE Adds 15-hour and 50-hour moving averages for trend analysis.
        """
        df = df.copy()

        # Moving averages
        df['MA_Short'] = df['Close'].rolling(window=self.ma_short_period).mean()
        df['MA_Long'] = df['Close'].rolling(window=self.ma_long_period).mean()

        logger.debug(
            "Technical indicators added",
            ma_short_last=df['MA_Short'].iloc[-1] if not pd.isna(df['MA_Short'].iloc[-1]) else None,
            ma_long_last=df['MA_Long'].iloc[-1] if not pd.isna(df['MA_Long'].iloc[-1]) else None,
        )

        return df

    def _calculate_macd(
        self,
        prices: pd.Series,
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9,
    ) -> dict[str, pd.Series]:
        """
        Calculate MACD indicator.

        Args:
            prices: Price series
            fast_period: Fast EMA period
            slow_period: Slow EMA period
            signal_period: Signal line period

        Returns:
            Dictionary with MACD, signal, and histogram series

        @MX:NOTE MACD calculation for momentum analysis.
        """
        ema_fast = prices.ewm(span=fast_period, adjust=False).mean()
        ema_slow = prices.ewm(span=slow_period, adjust=False).mean()
        macd = ema_fast - ema_slow
        signal = macd.ewm(span=signal_period, adjust=False).mean()
        histogram = macd - signal

        return {
            'macd': macd,
            'signal': signal,
            'histogram': histogram,
        }

    async def cleanup_old_charts(self, max_age_hours: int = 24) -> None:
        """
        Remove chart images older than specified age.

        Args:
            max_age_hours: Maximum age in hours before cleanup

        @MX:NOTE Automatic cleanup prevents disk space accumulation.
        """
        cutoff = datetime.now() - timedelta(hours=max_age_hours)
        removed = 0

        for chart_file in self.output_dir.glob("*.png"):
            if datetime.fromtimestamp(chart_file.stat().st_mtime) < cutoff:
                chart_file.unlink()
                removed += 1

        if removed > 0:
            logger.info("Cleaned up old chart files", removed=removed)
