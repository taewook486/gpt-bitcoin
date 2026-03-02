"""
External API clients for the trading system.

This package contains clients for external services:
- GLMClient: ZhipuAI GLM API client for AI analysis
- UpbitClient: Upbit exchange API client for trading
"""

from gpt_bitcoin.infrastructure.external.glm_client import GLMClient
from gpt_bitcoin.infrastructure.external.upbit_client import UpbitClient

__all__ = ["GLMClient", "UpbitClient"]
