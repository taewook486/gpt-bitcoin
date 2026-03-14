"""
Pytest configuration and fixtures for GPT Bitcoin trading system tests.

This module provides mock fixtures for external APIs (OpenAI, Upbit, SerpApi)
to enable isolated testing without actual API calls.
"""

import json
import os
import sqlite3
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

# ============================================================================
# Module-level Mocks (installed before any test runs)
# ============================================================================


@pytest.fixture(scope="session", autouse=True)
def install_module_mocks():
    """
    Install mock modules that may not be installed in the test environment.

    This ensures tests can run without pandas_ta, selenium, etc.
    """
    # Mock pandas_ta
    if "pandas_ta" not in sys.modules:
        mock_ta = MagicMock()
        mock_ta.sma.return_value = pd.Series([100.0] * 30)
        mock_ta.ema.return_value = pd.Series([100.0] * 30)
        mock_ta.rsi.return_value = pd.Series([50.0] * 30)
        mock_ta.stoch.return_value = pd.DataFrame(
            {"STOCHk_14_3_3": [50.0] * 30, "STOCHd_14_3_3": [50.0] * 30}
        )
        sys.modules["pandas_ta"] = mock_ta

    # Mock selenium
    if "selenium" not in sys.modules:
        mock_selenium = MagicMock()
        mock_webdriver = MagicMock()
        mock_webdriver.Chrome = MagicMock()
        mock_selenium.webdriver = mock_webdriver

        mock_service = MagicMock()
        mock_selenium.webdriver.chrome.service = MagicMock()
        mock_selenium.webdriver.chrome.service.Service = mock_service

        mock_selenium.webdriver.common = MagicMock()
        mock_selenium.webdriver.common.by = MagicMock()
        mock_selenium.webdriver.common.by.By = MagicMock()

        mock_selenium.webdriver.support = MagicMock()
        mock_selenium.webdriver.support.ui = MagicMock()
        mock_selenium.webdriver.support.ui.WebDriverWait = MagicMock()
        mock_selenium.webdriver.support.expected_conditions = MagicMock()
        mock_selenium.webdriver.support.expected_conditions.EC = MagicMock()

        sys.modules["selenium"] = mock_selenium
        sys.modules["selenium.webdriver"] = mock_webdriver
        sys.modules["selenium.webdriver.chrome"] = mock_selenium.webdriver.chrome
        sys.modules["selenium.webdriver.chrome.service"] = mock_selenium.webdriver.chrome.service
        sys.modules["selenium.webdriver.common"] = mock_selenium.webdriver.common
        sys.modules["selenium.webdriver.common.by"] = mock_selenium.webdriver.common.by
        sys.modules["selenium.webdriver.support"] = mock_selenium.webdriver.support
        sys.modules["selenium.webdriver.support.ui"] = mock_selenium.webdriver.support.ui
        sys.modules["selenium.webdriver.support.expected_conditions"] = (
            mock_selenium.webdriver.support.expected_conditions
        )

    yield

    # Cleanup not strictly necessary for session scope


# ============================================================================
# Environment Setup
# ============================================================================


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """
    Set up test environment variables before running tests.

    This fixture automatically runs before all tests and sets required
    environment variables to mock values to prevent accidental API calls.
    """
    test_env = {
        "OPENAI_API_KEY": "test-openai-key-12345",
        "UPBIT_ACCESS_KEY": "test-upbit-access-key",
        "UPBIT_SECRET_KEY": "test-upbit-secret-key",
        "ZHIPUAI_API_KEY": "test-zhipuai-key",
        "SERPAPI_API_KEY": "test-serpapi-key",
    }

    # Store original values
    original_values = {}
    for key, value in test_env.items():
        original_values[key] = os.environ.get(key)
        os.environ[key] = value

    yield

    # Restore original values
    for key, original in original_values.items():
        if original is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = original


# ============================================================================
# Mock Fixtures for External APIs
# ============================================================================


@pytest.fixture
def mock_zhipuai():
    """
    Mock ZhipuAI client for testing without actual API calls.

    This fixture matches the real ZhipuAI SDK usage pattern.
    Returns a MagicMock that simulates ZhipuAI chat completions API responses.
    """
    with patch("zhipuai.ZhipuAI") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # Default mock response for chat completions
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content=json.dumps(
                        {
                            "decision": "hold",
                            "percentage": 0,
                            "reason": "Test response from mock",
                        }
                    )
                )
            )
        ]
        mock_client.chat.completions.create.return_value = mock_response

        yield mock_client


@pytest.fixture
def mock_openai_buy_decision():
    """
    Mock OpenAI client that returns a buy decision.
    """
    with patch("openai.OpenAI") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content=json.dumps(
                        {
                            "decision": "buy",
                            "percentage": 50,
                            "reason": "Test buy decision",
                        }
                    )
                )
            )
        ]
        mock_client.chat.completions.create.return_value = mock_response

        yield mock_client


@pytest.fixture
def mock_openai_sell_decision():
    """
    Mock OpenAI client that returns a sell decision.
    """
    with patch("openai.OpenAI") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content=json.dumps(
                        {
                            "decision": "sell",
                            "percentage": 100,
                            "reason": "Test sell decision",
                        }
                    )
                )
            )
        ]
        mock_client.chat.completions.create.return_value = mock_response

        yield mock_client


@pytest.fixture
def mock_upbit():
    """
    Mock pyupbit.Upbit client for testing without actual API calls.

    Returns a MagicMock that simulates Upbit exchange API responses.
    """
    with patch("pyupbit.Upbit") as mock_upbit_class:
        mock_client = MagicMock()
        mock_upbit_class.return_value = mock_client

        # Default balance response
        mock_client.get_balances.return_value = [
            {"currency": "KRW", "balance": "1000000.0"},
            {"currency": "BTC", "balance": "0.05", "avg_buy_price": "50000000"},
        ]
        mock_client.get_balance.return_value = 1000000.0

        # Default order response
        mock_client.buy_market_order.return_value = {
            "uuid": "test-buy-order-uuid",
            "side": "bid",
            "ord_type": "price",
            "price": "500000.0",
            "state": "done",
        }
        mock_client.sell_market_order.return_value = {
            "uuid": "test-sell-order-uuid",
            "side": "ask",
            "ord_type": "market",
            "volume": "0.025",
            "state": "done",
        }

        yield mock_client


@pytest.fixture
def mock_pyupbit_orderbook():
    """
    Mock pyupbit.get_orderbook function for testing.
    """
    with patch("pyupbit.get_orderbook") as mock_func:
        mock_func.return_value = {
            "timestamp": 1700000000000,
            "orderbook_units": [
                {"ask_price": 55000000, "bid_price": 54990000},
            ],
        }
        yield mock_func


@pytest.fixture
def mock_pyupbit_ohlcv():
    """
    Mock pyupbit.get_ohlcv function for testing.

    Returns sample OHLCV data suitable for technical indicator calculation.
    """
    sample_data = pd.DataFrame(
        {
            "open": [50000000 + i * 100000 for i in range(30)],
            "high": [51000000 + i * 100000 for i in range(30)],
            "low": [49000000 + i * 100000 for i in range(30)],
            "close": [50500000 + i * 100000 for i in range(30)],
            "volume": [100.0 + i * 10 for i in range(30)],
        },
        index=pd.date_range(start="2024-01-01", periods=30, freq="D"),
    )

    with patch("pyupbit.get_ohlcv") as mock_func:
        mock_func.return_value = sample_data.copy()
        yield mock_func


@pytest.fixture
def mock_serpapi():
    """
    Mock requests.get for SerpApi news data.

    Returns sample news results without making actual API calls.
    """
    sample_news = {
        "news_results": [
            {
                "title": "Bitcoin Price Reaches New High",
                "source": {"name": "CryptoNews"},
                "date": "01/15/2024, 10:30 AM, +0000 UTC",
            },
            {
                "stories": [
                    {
                        "title": "Market Analysis: BTC Trends",
                        "source": {"name": "CoinDesk"},
                        "date": "01/15/2024, 09:00 AM, +0000 UTC",
                    }
                ]
            },
        ]
    }

    with patch("requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.json.return_value = sample_news
        mock_get.return_value = mock_response
        yield mock_get


@pytest.fixture
def mock_fear_greed_api():
    """
    Mock requests.get for Fear and Greed Index API.

    Returns sample fear and greed index data.
    """
    sample_data = {
        "data": [
            {"value": "65", "value_classification": "Greed", "timestamp": "1705276800"},
            {"value": "60", "value_classification": "Greed", "timestamp": "1705190400"},
        ]
    }

    with patch("requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.json.return_value = sample_data
        mock_get.return_value = mock_response
        yield mock_get


@pytest.fixture
def mock_selenium():
    """
    Mock Selenium WebDriver for testing without browser automation.
    """
    with patch("selenium.webdriver.Chrome") as mock_chrome:
        mock_driver = MagicMock()
        mock_chrome.return_value = mock_driver

        # Mock screenshot behavior
        mock_driver.save_screenshot.return_value = True

        # Mock wait and element interactions
        mock_wait = MagicMock()
        with patch("selenium.webdriver.support.ui.WebDriverWait") as mock_wait_class:
            mock_wait_class.return_value = mock_wait
            mock_wait.until.return_value = MagicMock()
            mock_wait.until.return_value.click.return_value = None

            yield mock_driver


# ============================================================================
# Test Data Fixtures
# ============================================================================


@pytest.fixture
def sample_decision_buy():
    """
    Sample buy decision dictionary for testing.
    """
    return {"decision": "buy", "percentage": 50, "reason": "Test buy signal"}


@pytest.fixture
def sample_decision_sell():
    """
    Sample sell decision dictionary for testing.
    """
    return {"decision": "sell", "percentage": 100, "reason": "Test sell signal"}


@pytest.fixture
def sample_decision_hold():
    """
    Sample hold decision dictionary for testing.
    """
    return {"decision": "hold", "percentage": 0, "reason": "Market uncertain"}


@pytest.fixture
def sample_current_status():
    """
    Sample current status dictionary for testing.
    """
    return {
        "current_time": 1700000000000,
        "orderbook": {
            "timestamp": 1700000000000,
            "orderbook_units": [{"ask_price": 55000000, "bid_price": 54990000}],
        },
        "btc_balance": "0.05",
        "krw_balance": "1000000.0",
        "btc_avg_buy_price": "50000000",
    }


@pytest.fixture
def sample_ohlcv_daily():
    """
    Sample daily OHLCV DataFrame for testing.
    """
    return pd.DataFrame(
        {
            "open": [50000000 + i * 100000 for i in range(30)],
            "high": [51000000 + i * 100000 for i in range(30)],
            "low": [49000000 + i * 100000 for i in range(30)],
            "close": [50500000 + i * 100000 for i in range(30)],
            "volume": [100.0 + i * 10 for i in range(30)],
        },
        index=pd.date_range(start="2024-01-01", periods=30, freq="D"),
    )


@pytest.fixture
def sample_ohlcv_hourly():
    """
    Sample hourly OHLCV DataFrame for testing.
    """
    return pd.DataFrame(
        {
            "open": [50500000 + i * 10000 for i in range(24)],
            "high": [50600000 + i * 10000 for i in range(24)],
            "low": [50400000 + i * 10000 for i in range(24)],
            "close": [50550000 + i * 10000 for i in range(24)],
            "volume": [10.0 + i for i in range(24)],
        },
        index=pd.date_range(start="2024-01-15 00:00", periods=24, freq="h"),
    )


# ============================================================================
# Database Fixtures
# ============================================================================


@pytest.fixture
def temp_db_path(tmp_path: Path):
    """
    Temporary database path for testing.

    Creates a temporary SQLite database that is automatically cleaned up
    after the test.
    """
    db_path = tmp_path / "test_trading_decisions.sqlite"
    yield str(db_path)

    # Cleanup (ignore PermissionError on Windows due to SQLite file locking)
    if db_path.exists():
        try:
            db_path.unlink()
        except PermissionError:
            pass


@pytest.fixture
def initialized_test_db(temp_db_path: str):
    """
    Initialized test database with schema.

    Creates a test database with the decisions table schema.
    """
    with sqlite3.connect(temp_db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME,
                decision TEXT,
                percentage REAL,
                reason TEXT,
                btc_balance REAL,
                krw_balance REAL,
                btc_avg_buy_price REAL,
                btc_krw_price REAL
            );
        """
        )
        conn.commit()

    yield temp_db_path


@pytest.fixture
def populated_test_db(initialized_test_db: str):
    """
    Test database with sample decision records.
    """
    sample_decisions = [
        (
            "2024-01-15 08:01:00",
            "buy",
            50.0,
            "RSI oversold",
            0.025,
            500000.0,
            50000000.0,
            52000000.0,
        ),
        (
            "2024-01-15 16:01:00",
            "hold",
            0.0,
            "Waiting for confirmation",
            0.025,
            500000.0,
            50000000.0,
            52500000.0,
        ),
        (
            "2024-01-16 00:01:00",
            "sell",
            100.0,
            "Take profit target reached",
            0.05,
            250000.0,
            50000000.0,
            55000000.0,
        ),
    ]

    with sqlite3.connect(initialized_test_db) as conn:
        cursor = conn.cursor()
        cursor.executemany(
            """
            INSERT INTO decisions
            (timestamp, decision, percentage, reason, btc_balance,
             krw_balance, btc_avg_buy_price, btc_krw_price)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
            sample_decisions,
        )
        conn.commit()

    yield initialized_test_db


# ============================================================================
# Async Support
# ============================================================================


@pytest.fixture
def event_loop_policy():
    """
    Default event loop policy for async tests.
    """
    import asyncio

    return asyncio.DefaultEventLoopPolicy()


# ============================================================================
# Test Instructions File
# ============================================================================


@pytest.fixture
def temp_instructions_file(tmp_path: Path):
    """
    Temporary instructions file for testing.

    Creates a sample instructions.md file for GPT-4 prompts.
    """
    instructions_path = tmp_path / "instructions.md"
    instructions_content = """
# Trading Instructions

You are a Bitcoin trading assistant. Analyze the market data and make
trading decisions based on technical indicators.

## Decision Format

Respond with a JSON object containing:
- decision: "buy", "sell", or "hold"
- percentage: 0-100 (percentage of balance to trade)
- reason: explanation for the decision
"""
    instructions_path.write_text(instructions_content, encoding="utf-8")

    yield str(instructions_path)
