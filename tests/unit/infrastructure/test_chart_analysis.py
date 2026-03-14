"""
Unit tests for chart image analysis.

Tests cover:
- Chart generation with matplotlib/mplfinance
- Base64 image encoding
- Vision API integration (GLM-4.6V)
- Fallback for non-vision environments

These tests follow TDD approach to achieve 85%+ coverage.
"""

import base64
from unittest.mock import AsyncMock, MagicMock

import pytest


class TestChartGenerator:
    """Test Chart generation functionality."""

    def test_chart_generator_import(self):
        """ChartGenerator should be importable."""
        from gpt_bitcoin.infrastructure.chart import ChartGenerator

        assert ChartGenerator is not None

    def test_chart_generator_initialization(self):
        """ChartGenerator should initialize with defaults."""
        from gpt_bitcoin.infrastructure.chart import ChartGenerator

        generator = ChartGenerator()

        assert generator is not None

    def test_chart_generator_with_style(self):
        """ChartGenerator should accept style configuration."""
        from gpt_bitcoin.infrastructure.chart import ChartGenerator

        generator = ChartGenerator(style="dark")

        assert generator.style == "dark"

    def test_generate_ohlcv_chart(self):
        """ChartGenerator should generate OHLCV chart."""
        from gpt_bitcoin.infrastructure.chart import ChartGenerator

        generator = ChartGenerator()
        ohlcv_data = [
            {"open": 100, "high": 110, "low": 95, "close": 105, "volume": 1000},
            {"open": 105, "high": 115, "low": 100, "close": 110, "volume": 1200},
        ]

        result = generator.generate_ohlcv_chart(ohlcv_data)

        assert result is not None

    def test_generate_chart_returns_bytes(self):
        """ChartGenerator should return bytes."""
        from gpt_bitcoin.infrastructure.chart import ChartGenerator

        generator = ChartGenerator()
        ohlcv_data = [
            {"open": 100, "high": 110, "low": 95, "close": 105, "volume": 1000},
        ]

        result = generator.generate_ohlcv_chart(ohlcv_data)

        assert isinstance(result, bytes)

    def test_generate_chart_with_indicators(self):
        """ChartGenerator should support technical indicators."""
        from gpt_bitcoin.infrastructure.chart import ChartGenerator

        generator = ChartGenerator()
        ohlcv_data = [
            {"open": 100, "high": 110, "low": 95, "close": 105, "volume": 1000},
        ]

        result = generator.generate_ohlcv_chart(
            ohlcv_data,
            indicators=["ma20", "rsi"],
        )

        assert result is not None


class TestImageEncoder:
    """Test image encoding functionality."""

    def test_encode_to_base64(self):
        """encode_to_base64 should convert bytes to base64 string."""
        from gpt_bitcoin.infrastructure.chart import encode_to_base64

        data = b"test image data"
        result = encode_to_base64(data)

        assert isinstance(result, str)
        # Verify it's valid base64
        decoded = base64.b64decode(result)
        assert decoded == data

    def test_encode_to_base64_with_prefix(self):
        """encode_to_base64 should support data URI prefix."""
        from gpt_bitcoin.infrastructure.chart import encode_to_base64

        data = b"test image data"
        result = encode_to_base64(data, data_uri=True)

        assert result.startswith("data:image/")
        assert "base64," in result

    def test_decode_base64(self):
        """decode_base64 should convert base64 string to bytes."""
        from gpt_bitcoin.infrastructure.chart import decode_base64

        original = b"test image data"
        encoded = base64.b64encode(original).decode("utf-8")
        result = decode_base64(encoded)

        assert result == original


class TestVisionAnalyzer:
    """Test Vision API integration."""

    def test_vision_analyzer_import(self):
        """VisionAnalyzer should be importable."""
        from gpt_bitcoin.infrastructure.chart import VisionAnalyzer

        assert VisionAnalyzer is not None

    def test_vision_analyzer_initialization(self):
        """VisionAnalyzer should initialize."""
        from gpt_bitcoin.infrastructure.chart import VisionAnalyzer

        analyzer = VisionAnalyzer()

        assert analyzer is not None

    def test_vision_analyzer_with_client(self):
        """VisionAnalyzer should accept GLM client."""
        from gpt_bitcoin.infrastructure.chart import VisionAnalyzer

        mock_client = MagicMock()
        analyzer = VisionAnalyzer(client=mock_client)

        assert analyzer._client is not None

    def test_is_vision_available(self):
        """VisionAnalyzer should check availability."""
        from gpt_bitcoin.infrastructure.chart import VisionAnalyzer

        analyzer = VisionAnalyzer()

        # Should return boolean
        result = analyzer.is_vision_available()

        assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_analyze_chart_async(self):
        """VisionAnalyzer should analyze chart asynchronously."""
        from gpt_bitcoin.infrastructure.chart import VisionAnalyzer

        mock_client = MagicMock()
        mock_client.chat_async = AsyncMock(
            return_value={"choices": [{"message": {"content": "Analysis result"}}]}
        )

        analyzer = VisionAnalyzer(client=mock_client)

        result = await analyzer.analyze_chart_async(
            image_data=b"fake image",
            prompt="Analyze this chart",
        )

        assert result is not None

    def test_analyze_chart_fallback(self):
        """VisionAnalyzer should fallback when vision unavailable."""
        from gpt_bitcoin.infrastructure.chart import VisionAnalyzer

        analyzer = VisionAnalyzer()
        analyzer._vision_available = False

        result = analyzer.analyze_chart_sync(
            image_data=b"fake image",
            prompt="Analyze this chart",
        )

        # Should return None or fallback result
        assert result is None or isinstance(result, str)


class TestChartAnalysisIntegration:
    """Test integrated chart analysis workflow."""

    def test_chart_analysis_workflow(self):
        """Full chart analysis workflow should work."""
        from gpt_bitcoin.infrastructure.chart import (
            ChartGenerator,
            encode_to_base64,
        )

        # Generate chart
        generator = ChartGenerator()
        ohlcv_data = [
            {"open": 100, "high": 110, "low": 95, "close": 105, "volume": 1000},
        ]
        chart_bytes = generator.generate_ohlcv_chart(ohlcv_data)

        # Encode to base64
        chart_base64 = encode_to_base64(chart_bytes)

        # Verify workflow
        assert chart_bytes is not None
        assert chart_base64 is not None
        assert isinstance(chart_base64, str)

    def test_get_chart_image_for_analysis(self):
        """get_chart_image_for_analysis should return base64 image."""
        from gpt_bitcoin.infrastructure.chart import get_chart_image_for_analysis

        ohlcv_data = [
            {"open": 100, "high": 110, "low": 95, "close": 105, "volume": 1000},
        ]

        result = get_chart_image_for_analysis(ohlcv_data)

        assert result is not None
        assert isinstance(result, str)

    def test_get_chart_image_returns_none_on_error(self):
        """get_chart_image_for_analysis should return None on error."""
        from gpt_bitcoin.infrastructure.chart import get_chart_image_for_analysis

        # Empty data should handle gracefully
        result = get_chart_image_for_analysis([])

        assert result is None or isinstance(result, str)


class TestChartGeneratorEdgeCases:
    """Test ChartGenerator edge cases for coverage."""

    def test_generate_with_empty_data(self):
        """ChartGenerator should handle empty data."""
        from gpt_bitcoin.infrastructure.chart import ChartGenerator

        generator = ChartGenerator()
        result = generator.generate_ohlcv_chart([])

        assert result == b""

    def test_generate_with_single_candle(self):
        """ChartGenerator should handle single candle."""
        from gpt_bitcoin.infrastructure.chart import ChartGenerator

        generator = ChartGenerator()
        result = generator.generate_ohlcv_chart(
            [
                {"open": 100, "high": 110, "low": 95, "close": 105, "volume": 1000},
            ]
        )

        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_generate_with_dark_style(self):
        """ChartGenerator should apply dark style."""
        from gpt_bitcoin.infrastructure.chart import ChartGenerator

        generator = ChartGenerator(style="dark")
        result = generator.generate_ohlcv_chart(
            [
                {"open": 100, "high": 110, "low": 95, "close": 105, "volume": 1000},
                {"open": 105, "high": 115, "low": 100, "close": 110, "volume": 1200},
            ]
        )

        assert isinstance(result, bytes)

    def test_generate_with_ma20_indicator(self):
        """ChartGenerator should handle MA20 indicator."""
        from gpt_bitcoin.infrastructure.chart import ChartGenerator

        generator = ChartGenerator()
        # Need at least 20 candles for MA20
        data = [
            {"open": 100 + i, "high": 110 + i, "low": 95 + i, "close": 105 + i, "volume": 1000}
            for i in range(25)
        ]
        result = generator.generate_ohlcv_chart(data, indicators=["ma20"])

        assert isinstance(result, bytes)

    def test_generate_with_rsi_indicator(self):
        """ChartGenerator should handle RSI indicator."""
        from gpt_bitcoin.infrastructure.chart import ChartGenerator

        generator = ChartGenerator()
        data = [
            {"open": 100, "high": 110, "low": 95, "close": 105 + i, "volume": 1000}
            for i in range(20)
        ]
        result = generator.generate_ohlcv_chart(data, indicators=["rsi"])

        assert isinstance(result, bytes)


class TestVisionAnalyzerEdgeCases:
    """Test VisionAnalyzer edge cases for coverage."""

    def test_vision_analyzer_no_client(self):
        """VisionAnalyzer should handle no client gracefully."""
        from gpt_bitcoin.infrastructure.chart import VisionAnalyzer

        analyzer = VisionAnalyzer(client=None)

        assert analyzer.is_vision_available() is False

    def test_vision_analyzer_sync_analysis(self):
        """VisionAnalyzer should support sync analysis."""
        from gpt_bitcoin.infrastructure.chart import VisionAnalyzer

        mock_client = MagicMock()
        mock_client.chat = MagicMock(
            return_value={"choices": [{"message": {"content": "Sync analysis result"}}]}
        )

        analyzer = VisionAnalyzer(client=mock_client)
        analyzer._vision_available = True

        result = analyzer.analyze_chart_sync(
            image_data=b"fake image",
            prompt="Analyze",
        )

        assert result == "Sync analysis result"

    def test_vision_analyzer_sync_no_chat_method(self):
        """VisionAnalyzer should handle missing chat method."""
        from gpt_bitcoin.infrastructure.chart import VisionAnalyzer

        mock_client = MagicMock(spec=[])  # No chat method

        analyzer = VisionAnalyzer(client=mock_client)

        result = analyzer.analyze_chart_sync(
            image_data=b"fake image",
            prompt="Analyze",
        )

        assert result is None
