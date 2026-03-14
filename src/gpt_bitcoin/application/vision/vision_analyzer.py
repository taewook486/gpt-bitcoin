"""
Vision analyzer using GLM-4.6V Vision API for chart image analysis.

This module integrates GLM-4.6V Vision model to analyze
candlestick charts and extract structured trading signals.
"""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

from gpt_bitcoin.config.settings import Settings, get_settings
from gpt_bitcoin.domain.models.chart_analysis import (
    ChartAnalysis,
    CombinedAnalysis,
    Sentiment,
    Trend,
)
from gpt_bitcoin.infrastructure.exceptions import GLMAPIError
from gpt_bitcoin.infrastructure.external.glm_client import GLMClient
from gpt_bitcoin.infrastructure.logging import get_logger

logger = get_logger(__name__)


class VisionAnalyzer:
    """
    Analyze chart images using GLM-4.6V Vision API.

    @MX:NOTE Vision analyzer uses GLM-4.6V for chart pattern recognition.
    """

    def __init__(
        self,
        settings: Settings | None = None,
        glm_client: GLMClient | None = None,
    ):
        """
        Initialize Vision analyzer.

        Args:
            settings: Application settings (uses global if not provided)
            glm_client: GLM API client (creates new if not provided)
        """
        self._settings = settings or get_settings()
        self._glm_client = glm_client or GLMClient(settings=self._settings)

        # Vision analysis prompt
        self._system_prompt = """당신은 전문 암호화폐 기술 분석가입니다.

차트 이미지를 분석하여 다음 정보를 JSON 형식으로 제공해주세요:

1. **patterns**: 감지된 차트 패턴 리스트 (예: ["Hammer", "Bullish Engulfing"])
2. **trend**: 추세 방향 ("uptrend", "downtrend", "sideways")
3. **support_levels**: 지지선 가격 리스트 (숫자 배열)
4. **resistance_levels**: 저항선 가격 리스트 (숫자 배열)
5. **sentiment**: 시장 심리 ("bullish", "bearish", "neutral")
6. **confidence**: 분석 신뢰도 (0.0-1.0)

분석 기준:
- 캔들스틱 패턴: Hammer, Engulfing, Doji 등
- 이동평균 교차: 단기/장기 MA 위치 관계
- MACD 신호: MACD 라인과 시그널 라인 교차
- 거래량: 거래량 증가/감소 패턴
- 지지선/저항선: 이전 고점/저점 레벨

응답은 반드시 다음 JSON 형식이어야 합니다:
```json
{
  "patterns": ["Hammer"],
  "trend": "uptrend",
  "support_levels": [65000000, 64000000],
  "resistance_levels": [70000000, 71000000],
  "sentiment": "bullish",
  "confidence": 0.85
}
```"""

        logger.info("VisionAnalyzer initialized")

    async def analyze_chart(
        self,
        image_path: Path | str,
        coin_name: str = "BTC",
    ) -> ChartAnalysis:
        """
        Analyze chart image using GLM-4.6V Vision API.

        Args:
            image_path: Path to chart image file
            coin_name: Cryptocurrency name for context

        Returns:
            ChartAnalysis with structured vision analysis

        Raises:
            GLMAPIError: If Vision API call fails
            FileNotFoundError: If image file doesn't exist

        @MX:NOTE Vision API analyzes candlestick patterns and trend direction.
        """
        image_path = Path(image_path)
        if not image_path.exists():
            raise FileNotFoundError(f"Chart image not found: {image_path}")

        logger.info(
            "Analyzing chart with Vision API",
            image=str(image_path),
            coin=coin_name,
        )

        # Encode image to base64
        image_base64 = self._encode_image(image_path)

        # Prepare analysis message
        user_message = f"{coin_name}/KRW 차트를 분석해주세요. 기술적 지표와 패턴을 식별하고 JSON으로 응답해주세요."

        try:
            # Call Vision API
            response = await self._glm_client.analyze_with_vision(
                system_prompt=self._system_prompt,
                text_messages=[user_message],
                image_base64=image_base64,
                temperature=0.3,  # Lower temperature for more consistent analysis
            )

            # Parse response to ChartAnalysis
            analysis = ChartAnalysis.from_vision_response(response.content)

            logger.info(
                "Chart analysis completed",
                patterns=len(analysis.patterns),
                trend=analysis.trend.value,
                sentiment=analysis.sentiment.value,
                confidence=analysis.confidence,
            )

            return analysis

        except Exception as e:
            logger.error(
                "Vision API analysis failed",
                error=str(e),
                image=str(image_path),
            )
            raise GLMAPIError(
                f"Vision API analysis failed: {e}",
                model=self._settings.glm_vision_model,
            ) from e

    async def combine_analysis(
        self,
        vision: ChartAnalysis,
        technical_indicators: dict[str, Any],
    ) -> CombinedAnalysis:
        """
        Combine vision analysis with technical indicators for enhanced decision.

        Args:
            vision: Vision-based chart analysis
            technical_indicators: Technical indicator values (RSI, MA, etc.)

        Returns:
            CombinedAnalysis with merged signals

        @MX:ANCHOR Vision+Text combination logic - critical for trading decisions.
        """
        logger.info(
            "Combining vision and technical analysis",
            vision_trend=vision.trend.value,
            vision_sentiment=vision.sentiment.value,
            technical_keys=list(technical_indicators.keys()),
        )

        # Extract key technical indicators
        rsi = technical_indicators.get("rsi", 50)
        ma_short = technical_indicators.get("ma_short")
        ma_long = technical_indicators.get("ma_long")
        macd = technical_indicators.get("macd", {})
        fear_greed = technical_indicators.get("fear_greed_index", 50)

        # Determine text-based sentiment
        text_sentiment = self._determine_text_sentiment(
            rsi=rsi,
            ma_short=ma_short,
            ma_long=ma_long,
            macd=macd,
            fear_greed=fear_greed,
        )

        # Check agreement between vision and text
        agreement = self._check_agreement(vision.sentiment, text_sentiment)

        # Calculate combined sentiment
        combined_sentiment = self._combine_sentiments(
            vision_sentiment=vision.sentiment,
            text_sentiment=text_sentiment,
            vision_confidence=vision.confidence,
            agreement=agreement,
        )

        # Calculate combined confidence
        combined_confidence = self._calculate_combined_confidence(
            vision_confidence=vision.confidence,
            agreement=agreement,
            pattern_count=len(vision.patterns),
        )

        # Determine signal strength
        signal_strength = self._determine_signal_strength(
            combined_confidence=combined_confidence,
            agreement=agreement,
        )

        combined = CombinedAnalysis(
            vision=vision,
            technical_indicators=technical_indicators,
            combined_sentiment=combined_sentiment,
            combined_confidence=combined_confidence,
            signal_strength=signal_strength,
            agreement=agreement,
        )

        logger.info(
            "Combined analysis completed",
            combined_sentiment=combined_sentiment.value,
            combined_confidence=combined_confidence,
            signal_strength=signal_strength,
            agreement=agreement,
        )

        return combined

    def _encode_image(self, image_path: Path) -> str:
        """
        Encode image file to base64 string.

        Args:
            image_path: Path to image file

        Returns:
            Base64-encoded image string

        @MX:NOTE Image encoding for Vision API compatibility.
        """
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    def _determine_text_sentiment(
        self,
        rsi: float,
        ma_short: float | None,
        ma_long: float | None,
        macd: dict[str, Any],
        fear_greed: float,
    ) -> Sentiment:
        """
        Determine sentiment from technical indicators.

        Args:
            rsi: RSI value
            ma_short: Short-term moving average
            ma_long: Long-term moving average
            macd: MACD indicator values
            fear_greed: Fear & Greed Index

        Returns:
            Sentiment based on technical indicators

        @MX:NOTE Technical indicator sentiment calculation.
        """
        bullish_signals = 0
        bearish_signals = 0

        # RSI analysis
        if rsi < 30:
            bullish_signals += 1  # Oversold - bullish
        elif rsi > 70:
            bearish_signals += 1  # Overbought - bearish

        # Moving average analysis
        if ma_short is not None and ma_long is not None:
            if ma_short > ma_long:
                bullish_signals += 1  # Golden cross tendency
            else:
                bearish_signals += 1  # Death cross tendency

        # MACD analysis
        macd_value = macd.get("macd", 0)
        signal_value = macd.get("signal", 0)
        if macd_value > signal_value:
            bullish_signals += 1  # MACD above signal - bullish
        else:
            bearish_signals += 1  # MACD below signal - bearish

        # Fear & Greed analysis
        if fear_greed < 25:
            bullish_signals += 1  # Extreme fear - contrarian bullish
        elif fear_greed > 75:
            bearish_signals += 1  # Extreme greed - contrarian bearish

        # Determine overall sentiment
        if bullish_signals > bearish_signals:
            return Sentiment.BULLISH
        elif bearish_signals > bullish_signals:
            return Sentiment.BEARISH
        else:
            return Sentiment.NEUTRAL

    def _check_agreement(
        self,
        vision_sentiment: Sentiment,
        text_sentiment: Sentiment,
    ) -> bool:
        """
        Check if vision and text signals agree.

        Args:
            vision_sentiment: Vision-based sentiment
            text_sentiment: Text-based sentiment

        Returns:
            True if signals agree

        @MX:NOTE Signal agreement detection for confidence calculation.
        """
        return vision_sentiment == text_sentiment

    def _combine_sentiments(
        self,
        vision_sentiment: Sentiment,
        text_sentiment: Sentiment,
        vision_confidence: float,
        agreement: bool,
    ) -> Sentiment:
        """
        Combine vision and text sentiments into unified sentiment.

        Args:
            vision_sentiment: Vision-based sentiment
            text_sentiment: Text-based sentiment
            vision_confidence: Vision analysis confidence
            agreement: Whether signals agree

        Returns:
            Combined sentiment

        @MX:NOTE Weighted sentiment combination with agreement bonus.
        """
        if agreement:
            # High confidence when both agree
            return vision_sentiment
        else:
            # Weight by vision confidence when disagree
            if vision_confidence >= 0.7:
                return vision_sentiment
            else:
                # Lower vision confidence - use text signal
                return text_sentiment

    def _calculate_combined_confidence(
        self,
        vision_confidence: float,
        agreement: bool,
        pattern_count: int,
    ) -> float:
        """
        Calculate combined confidence score.

        Args:
            vision_confidence: Vision analysis confidence
            agreement: Whether vision and text signals agree
            pattern_count: Number of detected patterns

        Returns:
            Combined confidence score (0.0-1.0)

        @MX:NOTE Confidence calculation with agreement and pattern bonuses.
        """
        base_confidence = vision_confidence

        # Agreement bonus
        if agreement:
            base_confidence = min(1.0, base_confidence + 0.15)
        else:
            base_confidence = max(0.0, base_confidence - 0.10)

        # Pattern detection bonus (more patterns = higher confidence)
        if pattern_count >= 3:
            base_confidence = min(1.0, base_confidence + 0.10)

        return round(base_confidence, 2)

    def _determine_signal_strength(
        self,
        combined_confidence: float,
        agreement: bool,
    ) -> str:
        """
        Determine signal strength category.

        Args:
            combined_confidence: Combined confidence score
            agreement: Whether signals agree

        Returns:
            Signal strength: "strong", "medium", or "weak"

        @MX:NOTE Signal strength classification for trading decisions.
        """
        if combined_confidence >= 0.8 and agreement:
            return "strong"
        elif combined_confidence >= 0.6:
            return "medium"
        else:
            return "weak"

    async def analyze_text_only(
        self,
        technical_indicators: dict[str, Any],
    ) -> CombinedAnalysis:
        """
        Fallback text-only analysis when Vision API is unavailable.

        Args:
            technical_indicators: Technical indicator values

        Returns:
            CombinedAnalysis with text-only signals (reduced confidence)

        @MX:NOTE Fallback method for text-only analysis when Vision API fails.
        """
        logger.warning(
            "Using text-only fallback analysis",
            reason="Vision API unavailable",
        )

        # Determine text sentiment
        text_sentiment = self._determine_text_sentiment(technical_indicators)

        # Create placeholder vision analysis
        placeholder_vision = ChartAnalysis(
            patterns=[],
            trend=Trend.SIDEWAYS,
            support_levels=[],
            resistance_levels=[],
            sentiment=Sentiment.NEUTRAL,
            confidence=0.0,
            raw_response="Vision API unavailable - using text-only analysis",
        )

        # Combine with reduced confidence (no vision)
        combined = CombinedAnalysis(
            vision=placeholder_vision,
            technical_indicators=technical_indicators,
            combined_sentiment=text_sentiment,
            combined_confidence=0.5,  # Reduced confidence for text-only
            signal_strength="weak",  # Always weak without vision
            agreement=False,  # No vision to agree with
        )

        logger.info(
            "Text-only analysis completed",
            sentiment=text_sentiment.value,
            confidence=combined.combined_confidence,
        )

        return combined
