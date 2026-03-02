"""
Characterization tests for autotrade_v3.py (v2 legacy code).

These tests document the current behavior of the v2 trading system.
They capture WHAT the code does, not what it SHOULD do.

Version 2 Features:
- SQLite database for decision persistence
- News data from SerpApi
- Fear and Greed Index integration
- Percentage-based buy/sell execution
- Retry logic for GPT-4 responses
- Three daily schedules (00:01, 08:01, 16:01)

Characterization test naming convention: test_characterize_<component>_<scenario>
"""

import importlib.util
import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest


# Load the legacy module dynamically
# Note: autotrade_v2.py is the actual v2 code (with percentage, no selenium)
V2_MODULE_PATH = Path(__file__).parent.parent.parent / "autotrade_v2.py"


@pytest.fixture
def autotrade_v2_module():
    """
    Dynamically load autotrade_v3.py as a module for testing.
    """
    spec = importlib.util.spec_from_file_location("autotrade_v2", V2_MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules["autotrade_v2"] = module
    spec.loader.exec_module(module)
    return module


class TestCharacterizeInitializeDb:
    """
    Characterization tests for initialize_db function.

    Documents the current behavior of database initialization.
    """

    @pytest.mark.characterization
    def test_characterize_initialize_db_creates_table(
        self,
        autotrade_v2_module,
        temp_db_path,
    ):
        """
        CHARACTERIZES: Database table creation

        Current behavior:
        - Creates table named 'decisions' if not exists
        - Uses local timezone for timestamp (datetime('now', 'localtime'))
        - Has columns: id, timestamp, decision, percentage, reason,
                       btc_balance, krw_balance, btc_avg_buy_price, btc_krw_price
        """
        autotrade_v2_module.initialize_db(temp_db_path)

        # Document current behavior: table exists
        with sqlite3.connect(temp_db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='decisions'"
            )
            result = cursor.fetchone()

        assert result is not None, "Current behavior: creates 'decisions' table"

    @pytest.mark.characterization
    def test_characterize_initialize_db_schema(
        self,
        autotrade_v2_module,
        temp_db_path,
    ):
        """
        CHARACTERIZES: Database schema structure

        Current behavior:
        - id is INTEGER PRIMARY KEY AUTOINCREMENT
        - timestamp is DATETIME
        - percentage and balance columns are REAL
        - decision and reason are TEXT
        """
        autotrade_v2_module.initialize_db(temp_db_path)

        with sqlite3.connect(temp_db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(decisions)")
            columns = {row[1]: row[2] for row in cursor.fetchall()}

        # Document current behavior: expected column types
        expected_columns = {
            "id": "INTEGER",
            "timestamp": "DATETIME",
            "decision": "TEXT",
            "percentage": "REAL",
            "reason": "TEXT",
            "btc_balance": "REAL",
            "krw_balance": "REAL",
            "btc_avg_buy_price": "REAL",
            "btc_krw_price": "REAL",
        }

        for col_name, col_type in expected_columns.items():
            assert col_name in columns, f"Current behavior: has column '{col_name}'"
            assert columns[col_name] == col_type, (
                f"Current behavior: column '{col_name}' is {col_type}"
            )


class TestCharacterizeSaveDecisionToDb:
    """
    Characterization tests for save_decision_to_db function.

    Documents the current behavior of decision persistence.
    """

    @pytest.mark.characterization
    def test_characterize_save_decision_inserts_record(
        self,
        autotrade_v2_module,
        initialized_test_db,
        sample_decision_buy,
        sample_current_status,
        mock_pyupbit_orderbook,
    ):
        """
        CHARACTERIZES: Decision record insertion

        Current behavior:
        - Parses current_status from JSON string
        - Fetches current BTC price from orderbook
        - Uses datetime('now', 'localtime') for timestamp
        - Inserts all fields including current price
        """
        with patch("pyupbit.get_orderbook", mock_pyupbit_orderbook):
            with patch.object(
                autotrade_v2_module,
                "sqlite3",
                sqlite3,  # Use real sqlite3 but with test path
            ):
                # Override the db_path in the function
                original_connect = sqlite3.connect

                def mock_connect(path, *args, **kwargs):
                    if path == "trading_decisions.sqlite":
                        return original_connect(initialized_test_db, *args, **kwargs)
                    return original_connect(path, *args, **kwargs)

                with patch("sqlite3.connect", side_effect=mock_connect):
                    autotrade_v2_module.save_decision_to_db(
                        sample_decision_buy,
                        json.dumps(sample_current_status),
                    )

        # Document current behavior: record inserted
        with sqlite3.connect(initialized_test_db) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM decisions")
            count = cursor.fetchone()[0]

        assert count == 1, "Current behavior: inserts one record"

    @pytest.mark.characterization
    def test_characterize_save_decision_defaults(
        self,
        autotrade_v2_module,
        initialized_test_db,
        sample_current_status,
        mock_pyupbit_orderbook,
    ):
        """
        CHARACTERIZES: Default values for missing decision fields

        Current behavior:
        - percentage defaults to 100 if not provided
        - reason defaults to empty string if not provided
        """
        decision_without_optionals = {"decision": "buy"}

        with patch("pyupbit.get_orderbook", mock_pyupbit_orderbook):
            original_connect = sqlite3.connect

            def mock_connect(path, *args, **kwargs):
                if path == "trading_decisions.sqlite":
                    return original_connect(initialized_test_db, *args, **kwargs)
                return original_connect(path, *args, **kwargs)

            with patch("sqlite3.connect", side_effect=mock_connect):
                autotrade_v2_module.save_decision_to_db(
                    decision_without_optionals,
                    json.dumps(sample_current_status),
                )

        # Document current behavior: defaults applied
        with sqlite3.connect(initialized_test_db) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT percentage, reason FROM decisions")
            row = cursor.fetchone()

        assert row[0] == 100, "Current behavior: percentage defaults to 100"
        assert row[1] == "", "Current behavior: reason defaults to empty string"


class TestCharacterizeFetchLastDecisions:
    """
    Characterization tests for fetch_last_decisions function.

    Documents the current behavior of decision history retrieval.
    """

    @pytest.mark.characterization
    def test_characterize_fetch_last_decisions_returns_formatted_string(
        self,
        autotrade_v2_module,
        populated_test_db,
    ):
        """
        CHARACTERIZES: Decision history retrieval

        Current behavior:
        - Returns newline-separated string of dict-like strings
        - Each decision is formatted as str(dict)
        - Orders by timestamp DESC
        - Converts timestamp to milliseconds since Unix epoch
        """
        result = autotrade_v2_module.fetch_last_decisions(populated_test_db, num_decisions=3)

        # Document current behavior: returns string
        assert isinstance(result, str), "Current behavior: returns string"

        # Document current behavior: contains multiple lines
        lines = result.strip().split("\n")
        assert len(lines) == 3, "Current behavior: returns requested number of decisions"

    @pytest.mark.characterization
    def test_characterize_fetch_last_decisions_empty_db(
        self,
        autotrade_v2_module,
        initialized_test_db,
    ):
        """
        CHARACTERIZES: Empty database handling

        Current behavior:
        - Returns "No decisions found." when table is empty
        """
        result = autotrade_v2_module.fetch_last_decisions(initialized_test_db)

        # Document current behavior: returns specific string
        assert result == "No decisions found.", (
            "Current behavior: returns 'No decisions found.' for empty db"
        )

    @pytest.mark.characterization
    def test_characterize_fetch_last_decisions_timestamp_format(
        self,
        autotrade_v2_module,
        populated_test_db,
    ):
        """
        CHARACTERIZES: Timestamp conversion to milliseconds

        Current behavior:
        - Parses timestamp from "%Y-%m-%d %H:%M:%S" format
        - Converts to milliseconds (multiplies by 1000)
        - Includes in output dict as 'timestamp' key
        """
        result = autotrade_v2_module.fetch_last_decisions(populated_test_db, num_decisions=1)

        # Document current behavior: contains timestamp in milliseconds
        # The format is str(dict) so we need to evaluate it
        # e.g., "{'timestamp': 1705276860000, 'decision': 'sell', ...}"
        assert "timestamp" in result, "Current behavior: contains 'timestamp' key"

        # Verify it's a large number (milliseconds since epoch)
        import re

        match = re.search(r"'timestamp':\s*(\d+)", result)
        assert match is not None, "Current behavior: timestamp is present"

        timestamp_ms = int(match.group(1))
        # Should be a reasonable timestamp (year 2020-2030 in milliseconds)
        assert timestamp_ms > 1577836800000, "Current behavior: timestamp in milliseconds"
        assert timestamp_ms < 1893456000000, "Current behavior: timestamp in reasonable range"


class TestCharacterizeGetNewsData:
    """
    Characterization tests for get_news_data function.

    Documents the current behavior of news data retrieval.
    """

    @pytest.mark.characterization
    def test_characterize_get_news_data_returns_string(
        self,
        autotrade_v2_module,
        mock_serpapi,
    ):
        """
        CHARACTERIZES: News data retrieval returns string

        Current behavior:
        - Makes GET request to SerpApi
        - Returns str(list) of tuples (title, source, timestamp)
        - Handles 'stories' nested structure
        """
        result = autotrade_v2_module.get_news_data()

        # Document current behavior: returns string
        assert isinstance(result, str), "Current behavior: returns string"

    @pytest.mark.characterization
    def test_characterize_get_news_data_error_handling(
        self,
        autotrade_v2_module,
        capsys,
    ):
        """
        CHARACTERIZES: Error handling in news retrieval

        Current behavior:
        - Returns "No news data available." on error
        - Prints error message to stdout
        """
        with patch("requests.get") as mock_get:
            mock_get.side_effect = Exception("API Error")
            result = autotrade_v2_module.get_news_data()

        # Document current behavior: returns fallback string
        assert result == "No news data available.", (
            "Current behavior: returns fallback on error"
        )

        # Document current behavior: prints error
        captured = capsys.readouterr()
        assert "Error fetching news data:" in captured.out, (
            "Current behavior: prints error message"
        )

    @pytest.mark.characterization
    def test_characterize_get_news_data_missing_date(
        self,
        autotrade_v2_module,
    ):
        """
        CHARACTERIZES: Handling of news items without date

        Current behavior:
        - Uses "No timestamp provided" for items without date
        - Still includes the news item in results
        """
        news_without_date = {
            "news_results": [
                {"title": "Breaking News", "source": {"name": "TestSource"}},
            ]
        }

        with patch("requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.json.return_value = news_without_date
            mock_get.return_value = mock_response
            result = autotrade_v2_module.get_news_data()

        # Document current behavior: includes item with "No timestamp provided"
        assert "No timestamp provided" in result, (
            "Current behavior: handles missing date with placeholder"
        )


class TestCharacterizeFetchFearAndGreedIndex:
    """
    Characterization tests for fetch_fear_and_greed_index function.

    Documents the current behavior of Fear and Greed Index retrieval.
    """

    @pytest.mark.characterization
    def test_characterize_fetch_fear_greed_returns_string(
        self,
        autotrade_v2_module,
        mock_fear_greed_api,
    ):
        """
        CHARACTERIZES: Fear and Greed Index retrieval

        Current behavior:
        - Returns concatenated str(dict) for each data item
        - Supports limit and date_format parameters
        """
        result = autotrade_v2_module.fetch_fear_and_greed_index(limit=2)

        # Document current behavior: returns string
        assert isinstance(result, str), "Current behavior: returns string"

        # Document current behavior: contains expected data
        assert "value" in result, "Current behavior: contains 'value'"
        assert "value_classification" in result, (
            "Current behavior: contains 'value_classification'"
        )


class TestCharacterizeExecuteBuyWithPercentage:
    """
    Characterization tests for execute_buy function (v2 with percentage).

    Documents the current behavior of percentage-based buy execution.
    """

    @pytest.mark.characterization
    def test_characterize_execute_buy_with_percentage(
        self,
        autotrade_v2_module,
        mock_upbit,
        capsys,
    ):
        """
        CHARACTERIZES: Percentage-based buy execution

        Current behavior:
        - Gets KRW balance
        - Calculates amount = balance * (percentage / 100)
        - Adjusts for fees (0.9995 multiplier)
        - Minimum threshold check: amount > 5000
        """
        mock_upbit.get_balance.return_value = 1000000.0  # 1M KRW

        with patch.object(autotrade_v2_module, "upbit", mock_upbit):
            autotrade_v2_module.execute_buy(50)  # 50%

        # Document current behavior: buys 50% of balance with fee adjustment
        mock_upbit.buy_market_order.assert_called_once()
        call_args = mock_upbit.buy_market_order.call_args
        # 1000000 * 0.5 * 0.9995 = 499750.0
        assert call_args[0][1] == 499750.0, (
            "Current behavior: 50% of balance with 0.05% fee adjustment"
        )

    @pytest.mark.characterization
    def test_characterize_execute_buy_percentage_prints_status(
        self,
        autotrade_v2_module,
        mock_upbit,
        capsys,
    ):
        """
        CHARACTERIZES: Status message includes percentage

        Current behavior:
        - Prints "Attempting to buy BTC with a percentage of KRW balance..."
        """
        mock_upbit.get_balance.return_value = 1000000.0

        with patch.object(autotrade_v2_module, "upbit", mock_upbit):
            autotrade_v2_module.execute_buy(25)

        captured = capsys.readouterr()
        assert "percentage of KRW balance" in captured.out, (
            "Current behavior: mentions percentage in status message"
        )


class TestCharacterizeExecuteSellWithPercentage:
    """
    Characterization tests for execute_sell function (v2 with percentage).

    Documents the current behavior of percentage-based sell execution.
    """

    @pytest.mark.characterization
    def test_characterize_execute_sell_with_percentage(
        self,
        autotrade_v2_module,
        mock_upbit,
        mock_pyupbit_orderbook,
        capsys,
    ):
        """
        CHARACTERIZES: Percentage-based sell execution

        Current behavior:
        - Gets BTC balance
        - Calculates amount = balance * (percentage / 100)
        - Gets current price to check minimum threshold
        - Minimum threshold check: price * amount > 5000
        """
        mock_upbit.get_balance.return_value = 0.1  # 0.1 BTC

        with patch.object(autotrade_v2_module, "upbit", mock_upbit):
            with patch("pyupbit.get_orderbook", mock_pyupbit_orderbook):
                autotrade_v2_module.execute_sell(50)  # 50%

        # Document current behavior: sells 50% of balance
        mock_upbit.sell_market_order.assert_called_once()
        call_args = mock_upbit.sell_market_order.call_args
        assert call_args[0][1] == 0.05, "Current behavior: sells 50% of 0.1 BTC"


class TestCharacterizeMakeDecisionAndExecute:
    """
    Characterization tests for make_decision_and_execute function (v2).

    Documents the current behavior of the main decision loop with retry logic.
    """

    @pytest.mark.characterization
    def test_characterize_make_decision_retry_logic(
        self,
        autotrade_v2_module,
        mock_upbit,
        mock_pyupbit_ohlcv,
        mock_pyupbit_orderbook,
        mock_serpapi,
        mock_fear_greed_api,
        capsys,
    ):
        """
        CHARACTERIZES: Retry logic for JSON parsing failures

        Current behavior:
        - Max 5 retries
        - 5 second delay between retries
        - Prints retry status to stdout
        - Continues until valid JSON or max retries
        """
        # Create mock that fails first time, succeeds second time
        mock_client = MagicMock()
        fail_response = MagicMock()
        fail_response.choices = [MagicMock(message=MagicMock(content="Invalid JSON"))]

        success_response = MagicMock()
        success_response.choices = [
            MagicMock(
                message=MagicMock(
                    content=json.dumps({"decision": "hold", "percentage": 0, "reason": "Test"})
                )
            )
        ]

        mock_client.chat.completions.create.side_effect = [
            fail_response,
            success_response,
        ]

        with patch.object(autotrade_v2_module, "client", mock_client):
            with patch.object(autotrade_v2_module, "upbit", mock_upbit):
                with patch("pyupbit.get_ohlcv", mock_pyupbit_ohlcv):
                    with patch("pyupbit.get_orderbook", mock_pyupbit_orderbook):
                        with patch.object(
                            autotrade_v2_module,
                            "get_instructions",
                            return_value="Test",
                        ):
                            # Patch time.sleep to avoid delay
                            with patch("time.sleep"):
                                autotrade_v2_module.make_decision_and_execute()

        # Document current behavior: prints retry message
        captured = capsys.readouterr()
        assert "JSON parsing failed:" in captured.out, (
            "Current behavior: prints JSON parse error"
        )
        assert "Retrying in 5 seconds..." in captured.out, (
            "Current behavior: prints retry message"
        )
        assert "Attempt 2 of 5" in captured.out, (
            "Current behavior: prints attempt number"
        )

    @pytest.mark.characterization
    def test_characterize_make_decision_max_retries_exceeded(
        self,
        autotrade_v2_module,
        mock_upbit,
        mock_pyupbit_ohlcv,
        mock_pyupbit_orderbook,
        capsys,
    ):
        """
        CHARACTERIZES: Max retries exceeded handling

        Current behavior:
        - Returns early after max retries
        - Prints "Failed to make a decision after maximum retries."
        """
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Invalid"))]
        mock_client.chat.completions.create.return_value = mock_response

        with patch.object(autotrade_v2_module, "client", mock_client):
            with patch.object(autotrade_v2_module, "upbit", mock_upbit):
                with patch("pyupbit.get_ohlcv", mock_pyupbit_ohlcv):
                    with patch("pyupbit.get_orderbook", mock_pyupbit_orderbook):
                        with patch.object(
                            autotrade_v2_module,
                            "get_instructions",
                            return_value="Test",
                        ):
                            with patch("time.sleep"):
                                autotrade_v2_module.make_decision_and_execute()

        captured = capsys.readouterr()
        assert "Failed to make a decision after maximum retries." in captured.out, (
            "Current behavior: prints max retries message"
        )

    @pytest.mark.characterization
    def test_characterize_make_decision_calls_all_data_sources(
        self,
        autotrade_v2_module,
        mock_openai,
        mock_upbit,
        mock_pyupbit_ohlcv,
        mock_pyupbit_orderbook,
        mock_serpapi,
        mock_fear_greed_api,
        initialized_test_db,
    ):
        """
        CHARACTERIZES: All data sources are called

        Current behavior:
        - Calls get_news_data()
        - Calls fetch_and_prepare_data()
        - Calls fetch_last_decisions()
        - Calls fetch_fear_and_greed_index(limit=30)
        - Calls get_current_status()
        """
        with patch.object(autotrade_v2_module, "client", mock_openai):
            with patch.object(autotrade_v2_module, "upbit", mock_upbit):
                with patch("pyupbit.get_ohlcv", mock_pyupbit_ohlcv):
                    with patch("pyupbit.get_orderbook", mock_pyupbit_orderbook):
                        with patch.object(
                            autotrade_v2_module,
                            "get_instructions",
                            return_value="Test",
                        ):
                            # Patch fetch_last_decisions to use test db
                            original_connect = sqlite3.connect

                            def mock_connect(path, *args, **kwargs):
                                if path == "trading_decisions.sqlite":
                                    return original_connect(
                                        initialized_test_db, *args, **kwargs
                                    )
                                return original_connect(path, *args, **kwargs)

                            with patch("sqlite3.connect", side_effect=mock_connect):
                                autotrade_v2_module.make_decision_and_execute()

        # Document current behavior: GPT-4 called with multiple inputs
        mock_openai.chat.completions.create.assert_called_once()
        call_kwargs = mock_openai.chat.completions.create.call_args
        messages = call_kwargs[1]["messages"]

        # Should have system message + 5 user messages
        assert len(messages) == 6, (
            "Current behavior: 1 system + 5 user messages (news, data, decisions, fear_greed, status)"
        )


class TestCharacterizeAnalyzeDataWithGpt4:
    """
    Characterization tests for analyze_data_with_gpt4 function (v2).

    Documents the current behavior of GPT-4 interaction with multiple inputs.
    """

    @pytest.mark.characterization
    def test_characterize_analyze_uses_gpt4_turbo(
        self,
        autotrade_v2_module,
        mock_openai,
    ):
        """
        CHARACTERIZES: Uses gpt-4-turbo-preview model

        Current behavior:
        - Model name: "gpt-4-turbo-preview"
        - response_format: {"type": "json_object"}
        """
        with patch.object(autotrade_v2_module, "client", mock_openai):
            with patch.object(
                autotrade_v2_module,
                "get_instructions",
                return_value="Test",
            ):
                autotrade_v2_module.analyze_data_with_gpt4(
                    "news", "data", "decisions", "fear_greed", "status"
                )

        call_kwargs = mock_openai.chat.completions.create.call_args[1]

        # Document current behavior: uses gpt-4-turbo-preview
        assert call_kwargs["model"] == "gpt-4-turbo-preview", (
            "Current behavior: uses gpt-4-turbo-preview model"
        )

        # Document current behavior: requests JSON response
        assert call_kwargs["response_format"] == {"type": "json_object"}, (
            "Current behavior: requests JSON response format"
        )

    @pytest.mark.characterization
    def test_characterize_analyze_reads_instructions_v2(
        self,
        autotrade_v2_module,
        mock_openai,
    ):
        """
        CHARACTERIZES: Reads from instructions_v2.md

        Current behavior:
        - Instructions file path: "instructions_v2.md"
        """
        with patch.object(autotrade_v2_module, "client", mock_openai):
            with patch.object(
                autotrade_v2_module,
                "get_instructions",
            ) as mock_get_instructions:
                mock_get_instructions.return_value = "Test instructions"
                autotrade_v2_module.analyze_data_with_gpt4(
                    "news", "data", "decisions", "fear_greed", "status"
                )

        # Document current behavior: reads instructions_v2.md
        mock_get_instructions.assert_called_once_with("instructions_v2.md")
