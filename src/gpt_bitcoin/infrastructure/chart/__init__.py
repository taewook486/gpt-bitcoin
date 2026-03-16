"""
Chart image analysis module.

This module provides:
- Chart generation with matplotlib/mplfinance
- Base64 image encoding for API transmission
- Vision API integration (GLM-4.6V)
- Fallback for non-vision environments

@MX:NOTE: Implements SPEC-MODERNIZE-001 Section 8.3 chart image analysis requirements.
"""

from __future__ import annotations

import base64
import io
from typing import Any

from gpt_bitcoin.infrastructure.logging import get_logger


class ChartGenerator:
    """
    Generate candlestick charts from OHLCV data.

    Uses matplotlib for chart generation with optional
    technical indicators overlay.

    Example:
        ```python
        generator = ChartGenerator(style="dark")
        chart_bytes = generator.generate_ohlcv_chart(ohlcv_data)
        base64_image = encode_to_base64(chart_bytes)
        ```
    """

    def __init__(self, style: str = "default"):
        """
        Initialize ChartGenerator.

        Args:
            style: Chart style ("default", "dark")
        """
        self._style = style
        self._logger = get_logger("chart_generator")

    @property
    def style(self) -> str:
        """Get chart style."""
        return self._style

    def generate_ohlcv_chart(
        self,
        ohlcv_data: list[dict[str, Any]],
        indicators: list[str] | None = None,
    ) -> bytes:
        """
        Generate OHLCV candlestick chart.

        Args:
            ohlcv_data: List of OHLCV dictionaries with keys:
                open, high, low, close, volume
            indicators: Optional list of indicators to overlay
                Supported: ma20, rsi, bb (bollinger bands)

        Returns:
            Chart image as bytes (PNG format)

        @MX:WARN: Requires matplotlib package for chart generation.
        """
        if not ohlcv_data:
            self._logger.warning("Empty OHLCV data provided")
            return b""

        try:
            import matplotlib

            matplotlib.use("Agg")  # Non-interactive backend
            from datetime import datetime

            import matplotlib.dates as mdates
            import matplotlib.pyplot as plt

            # Create figure with subplots
            fig, (ax1, ax2) = plt.subplots(
                2,
                1,
                figsize=(12, 8),
                gridspec_kw={"height_ratios": [3, 1]},
            )

            # Set style
            if self._style == "dark":
                fig.patch.set_facecolor("#1a1a2e")
                ax1.set_facecolor("#1a1a2e")
                ax2.set_facecolor("#1a1a2e")
                text_color = "white"
            else:
                text_color = "black"

            # Extract data
            opens = [d.get("open", 0) for d in ohlcv_data]
            highs = [d.get("high", 0) for d in ohlcv_data]
            lows = [d.get("low", 0) for d in ohlcv_data]
            closes = [d.get("close", 0) for d in ohlcv_data]
            volumes = [d.get("volume", 0) for d in ohlcv_data]

            # Plot candlesticks
            x = range(len(ohlcv_data))
            for i, (o, h, l, c) in enumerate(zip(opens, highs, lows, closes)):
                color = "green" if c >= o else "red"
                # Candle body
                ax1.bar(i, abs(c - o), bottom=min(o, c), color=color, width=0.6)
                # Wicks
                ax1.vlines(i, l, h, color=color, linewidth=1)

            # Plot volume
            colors = ["green" if c >= o else "red" for o, c in zip(opens, closes)]
            ax2.bar(x, volumes, color=colors, width=0.6)

            # Add indicators if specified
            if indicators:
                if "ma20" in indicators and len(closes) >= 20:
                    ma20 = self._calculate_ma(closes, 20)
                    ax1.plot(x[19:], ma20, color="yellow", linewidth=1, label="MA20")

                if "rsi" in indicators and len(closes) >= 14:
                    rsi = self._calculate_rsi(closes)
                    ax_rsi = ax1.twinx()
                    ax_rsi.plot(x, rsi, color="purple", linewidth=1, label="RSI")
                    ax_rsi.set_ylabel("RSI", color=text_color)
                    ax_rsi.tick_params(axis="y", labelcolor=text_color)

            # Styling
            ax1.set_ylabel("Price", color=text_color)
            ax1.set_title("Price Chart", color=text_color)
            ax1.tick_params(axis="both", colors=text_color)

            ax2.set_ylabel("Volume", color=text_color)
            ax2.set_xlabel("Time", color=text_color)
            ax2.tick_params(axis="both", colors=text_color)

            plt.tight_layout()

            # Save to bytes
            buf = io.BytesIO()
            plt.savefig(buf, format="png", dpi=100)
            buf.seek(0)
            plt.close(fig)

            return buf.getvalue()

        except ImportError:
            self._logger.error("matplotlib not available, returning empty bytes")
            return b""
        except Exception as e:
            self._logger.error("Chart generation failed", error=str(e))
            return b""

    def _calculate_ma(self, data: list[float], period: int) -> list[float]:
        """Calculate Moving Average."""
        result = []
        for i in range(period - 1, len(data)):
            avg = sum(data[i - period + 1 : i + 1]) / period
            result.append(avg)
        return result

    def _calculate_rsi(self, closes: list[float], period: int = 14) -> list[float]:
        """Calculate Relative Strength Index."""
        if len(closes) < period + 1:
            return [50.0] * len(closes)  # Default neutral RSI

        rsi_values = [50.0] * period  # Initial values

        gains = []
        losses = []

        for i in range(1, len(closes)):
            change = closes[i] - closes[i - 1]
            gains.append(max(0, change))
            losses.append(max(0, -change))

        for i in range(period, len(gains)):
            avg_gain = sum(gains[i - period : i]) / period
            avg_loss = sum(losses[i - period : i]) / period

            if avg_loss == 0:
                rsi = 100.0
            else:
                rs = avg_gain / avg_loss
                rsi = 100 - (100 / (1 + rs))

            rsi_values.append(rsi)

        return rsi_values


def encode_to_base64(data: bytes, data_uri: bool = False) -> str:
    """
    Encode bytes to base64 string.

    Args:
        data: Binary data to encode
        data_uri: If True, return as data URI with image/png prefix

    Returns:
        Base64 encoded string

    Example:
        ```python
        chart_bytes = generator.generate_ohlcv_chart(data)
        base64_str = encode_to_base64(chart_bytes)
        # Or with data URI:
        data_uri = encode_to_base64(chart_bytes, data_uri=True)
        # Returns: "data:image/png;base64,iVBORw0KGgo..."
        ```
    """
    encoded = base64.b64encode(data).decode("utf-8")

    if data_uri:
        return f"data:image/png;base64,{encoded}"

    return encoded


def decode_base64(encoded: str) -> bytes:
    """
    Decode base64 string to bytes.

    Args:
        encoded: Base64 encoded string (with or without data URI prefix)

    Returns:
        Decoded bytes
    """
    # Remove data URI prefix if present
    if encoded.startswith("data:"):
        encoded = encoded.split(",", 1)[1]

    return base64.b64decode(encoded)


class VisionAnalyzer:
    """
    Analyze charts using GLM-4.6V Vision API.

    Provides both async and sync methods for chart analysis
    with fallback for non-vision environments.

    Example:
        ```python
        analyzer = VisionAnalyzer(client=glm_client)
        if analyzer.is_vision_available():
            analysis = await analyzer.analyze_chart_async(image_data, prompt)
        ```
    """

    def __init__(self, client: Any = None):
        """
        Initialize VisionAnalyzer.

        Args:
            client: GLM client instance (optional)
        """
        self._client = client
        self._logger = get_logger("vision_analyzer")
        self._vision_available = self._check_vision_availability()

    def _check_vision_availability(self) -> bool:
        """Check if vision capabilities are available."""
        if self._client is None:
            return False

        # Check if client has vision method
        return hasattr(self._client, "chat_async") or hasattr(self._client, "chat")

    def is_vision_available(self) -> bool:
        """
        Check if vision analysis is available.

        Returns:
            True if vision API is configured and available
        """
        return self._vision_available

    async def analyze_chart_async(
        self,
        image_data: bytes,
        prompt: str,
    ) -> str | None:
        """
        Analyze chart image asynchronously.

        Args:
            image_data: Chart image as bytes
            prompt: Analysis prompt

        Returns:
            Analysis result string or None if unavailable
        """
        if not self._vision_available:
            self._logger.warning("Vision analysis not available")
            return None

        try:
            # Encode image to base64
            image_base64 = encode_to_base64(image_data)

            # Prepare message with image
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{image_base64}"},
                        },
                    ],
                }
            ]

            # Call vision API
            if hasattr(self._client, "chat_async"):
                response = await self._client.chat_async(messages=messages)
            else:
                response = self._client.chat(messages=messages)

            # Extract result
            if response and "choices" in response:
                return response["choices"][0]["message"]["content"]

            return None

        except Exception as e:
            self._logger.error("Vision analysis failed", error=str(e))
            return None

    def analyze_chart_sync(
        self,
        image_data: bytes,
        prompt: str,
    ) -> str | None:
        """
        Analyze chart image synchronously.

        Args:
            image_data: Chart image as bytes
            prompt: Analysis prompt

        Returns:
            Analysis result string or None if unavailable
        """
        if not self._vision_available:
            return None

        try:
            image_base64 = encode_to_base64(image_data)

            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{image_base64}"},
                        },
                    ],
                }
            ]

            if hasattr(self._client, "chat"):
                response = self._client.chat(messages=messages)

                if response and "choices" in response:
                    return response["choices"][0]["message"]["content"]

            return None

        except Exception as e:
            self._logger.error("Sync vision analysis failed", error=str(e))
            return None


def get_chart_image_for_analysis(
    ohlcv_data: list[dict[str, Any]],
    indicators: list[str] | None = None,
    style: str = "dark",
) -> str | None:
    """
    Generate chart and return as base64 string for API analysis.

    This is a convenience function that combines chart generation
    and base64 encoding for easy integration with vision APIs.

    Args:
        ohlcv_data: List of OHLCV dictionaries
        indicators: Optional indicators to overlay
        style: Chart style ("default" or "dark")

    Returns:
        Base64 encoded chart image or None on error

    Example:
        ```python
        chart_base64 = get_chart_image_for_analysis(ohlcv_data)
        if chart_base64:
            analysis = await vision_analyzer.analyze(chart_base64)
        ```
    """
    if not ohlcv_data:
        return None

    try:
        generator = ChartGenerator(style=style)
        chart_bytes = generator.generate_ohlcv_chart(ohlcv_data, indicators)

        if not chart_bytes:
            return None

        return encode_to_base64(chart_bytes)

    except Exception as e:
        get_logger("chart").error("Failed to generate chart for analysis", error=str(e))
        return None


__all__ = [
    "ChartGenerator",
    "VisionAnalyzer",
    "decode_base64",
    "encode_to_base64",
    "get_chart_image_for_analysis",
]
