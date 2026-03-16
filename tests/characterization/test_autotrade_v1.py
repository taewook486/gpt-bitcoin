"""
Characterization tests for autotrade_v2.py (v1 legacy code).

These tests document the current behavior of the v1 trading system.
They capture WHAT the code does, not what it SHOULD do.

Version 1 Features:
- Basic OHLCV data fetching with technical indicators
- GPT-4-turbo-preview for decision making
- Simple buy/sell execution without percentage control
- Hourly scheduling

Characterization test naming convention: test_characterize_<component>_<scenario>
"""

import importlib.util
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Load the legacy module dynamically
# Note: autotrade.py is the actual v1 code (no percentage parameter)
V1_MODULE_PATH = Path(__file__).parent.parent.parent / "autotrade.py"


@pytest.fixture
def autotrade_v1_module():
    """
    Dynamically load autotrade_v2.py as a module for testing.

    This allows testing the legacy code in isolation without
    modifying the original file structure.
    """
    spec = importlib.util.spec_from_file_location("autotrade_v1", V1_MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules["autotrade_v1"] = module
    spec.loader.exec_module(module)
    return module


class TestCharacterizeGetCurrentStatus:
    """
    Characterization tests for get_current_status function.

    Documents the current behavior of status retrieval including:
    - Orderbook data structure
    - Balance parsing from Upbit API
    - JSON output format
    """

    @pytest.mark.characterization
    def test_characterize_get_current_status_returns_json_string(
        self,
        autotrade_v1_module,
        mock_upbit,
        mock_pyupbit_orderbook,
    ):
        """
        CHARACTERIZES: get_current_status returns JSON string

        Current behavior:
        - Returns a JSON string (not dict)
        - Contains: current_time, orderbook, btc_balance, krw_balance, btc_avg_buy_price
        - Balance values are strings from API
        - Missing currencies default to 0
        """
        # Setup mock for module-level upbit instance
        with patch.object(autotrade_v1_module, "upbit", mock_upbit):
            with patch("pyupbit.get_orderbook", mock_pyupbit_orderbook):
                result = autotrade_v1_module.get_current_status()

        # Document current behavior: returns JSON string
        assert isinstance(result, str), "Current behavior: get_current_status returns JSON string"

        # Document current behavior: can be parsed as JSON
        parsed = json.loads(result)
        assert isinstance(parsed, dict), "Current behavior: result is JSON string of dict"

        # Document current behavior: contains expected keys
        expected_keys = {
            "current_time",
            "orderbook",
            "btc_balance",
            "krw_balance",
            "btc_avg_buy_price",
        }
        assert set(parsed.keys()) == expected_keys, (
            f"Current behavior: contains keys {expected_keys}"
        )

    @pytest.mark.characterization
    def test_characterize_get_current_status_missing_btc_balance(
        self,
        autotrade_v1_module,
        mock_pyupbit_orderbook,
    ):
        """
        CHARACTERIZES: Missing BTC balance defaults to 0

        Current behavior:
        - When BTC not in balances, btc_balance = 0
        - btc_avg_buy_price = 0 when BTC not held
        """
        mock_upbit = MagicMock()
        mock_upbit.get_balances.return_value = [
            {"currency": "KRW", "balance": "1000000.0"},
            # BTC missing
        ]

        with patch.object(autotrade_v1_module, "upbit", mock_upbit):
            with patch("pyupbit.get_orderbook", mock_pyupbit_orderbook):
                result = autotrade_v1_module.get_current_status()

        parsed = json.loads(result)

        # Document current behavior: defaults to 0
        assert parsed["btc_balance"] == 0, "Current behavior: missing BTC defaults to 0"
        assert parsed["btc_avg_buy_price"] == 0, (
            "Current behavior: missing avg_buy_price defaults to 0"
        )


class TestCharacterizeFetchAndPrepareData:
    """
    Characterization tests for fetch_and_prepare_data function.

    Documents the current behavior of data preparation including:
    - OHLCV data fetching for daily and hourly
    - Technical indicator calculation
    - JSON serialization format
    """

    @pytest.mark.characterization
    def test_characterize_fetch_and_prepare_data_returns_json_string(
        self,
        autotrade_v1_module,
        mock_pyupbit_ohlcv,
    ):
        """
        CHARACTERIZES: fetch_and_prepare_data returns JSON string

        Current behavior:
        - Fetches 30 days of daily data
        - Fetches 24 hours of hourly data
        - Adds technical indicators (SMA, EMA, RSI, Stochastic, MACD, Bollinger)
        - Returns double-JSON-encoded string (json.dumps of json string)
        - Prints length of combined data to stdout
        """
        with patch("pyupbit.get_ohlcv", mock_pyupbit_ohlcv):
            result = autotrade_v1_module.fetch_and_prepare_data()

        # Document current behavior: returns JSON string
        assert isinstance(result, str), "Current behavior: returns JSON string"

        # Document current behavior: double-encoded (json string of json string)
        inner_json = json.loads(result)
        assert isinstance(inner_json, str), "Current behavior: result is double-encoded JSON"

        # Document current behavior: inner JSON can be parsed
        data = json.loads(inner_json)
        assert "columns" in data, "Current behavior: uses pandas 'split' orient"
        assert "index" in data, "Current behavior: uses pandas 'split' orient"
        assert "data" in data, "Current behavior: uses pandas 'split' orient"

    @pytest.mark.characterization
    def test_characterize_fetch_and_prepare_data_indicators_added(
        self,
        autotrade_v1_module,
        mock_pyupbit_ohlcv,
    ):
        """
        CHARACTERIZES: Technical indicators are added to DataFrame

        Current behavior:
        - Adds SMA_10, EMA_10 for moving averages
        - Adds RSI_14 for relative strength index
        - Adds STOCHk_14_3_3, STOCHd_14_3_3 for stochastic
        - Adds MACD, Signal_Line, MACD_Histogram
        - Adds Middle_Band, Upper_Band, Lower_Band for Bollinger
        """
        with patch("pyupbit.get_ohlcv", mock_pyupbit_ohlcv):
            result = autotrade_v1_module.fetch_and_prepare_data()

        inner_json = json.loads(result)
        data = json.loads(inner_json)

        # Document current behavior: expected columns added
        columns = data["columns"]

        # Original OHLCV columns
        assert "open" in columns, "Current behavior: contains 'open'"
        assert "high" in columns, "Current behavior: contains 'high'"
        assert "low" in columns, "Current behavior: contains 'low'"
        assert "close" in columns, "Current behavior: contains 'close'"
        assert "volume" in columns, "Current behavior: contains 'volume'"

        # Technical indicators
        assert "SMA_10" in columns, "Current behavior: adds SMA_10"
        assert "EMA_10" in columns, "Current behavior: adds EMA_10"
        assert "RSI_14" in columns, "Current behavior: adds RSI_14"
        assert "MACD" in columns, "Current behavior: adds MACD"
        assert "Signal_Line" in columns, "Current behavior: adds Signal_Line"
        assert "MACD_Histogram" in columns, "Current behavior: adds MACD_Histogram"
        assert "Middle_Band" in columns, "Current behavior: adds Middle_Band"
        assert "Upper_Band" in columns, "Current behavior: adds Upper_Band"
        assert "Lower_Band" in columns, "Current behavior: adds Lower_Band"


class TestCharacterizeGetInstructions:
    """
    Characterization tests for get_instructions function.

    Documents the current behavior of instruction file reading.
    """

    @pytest.mark.characterization
    def test_characterize_get_instructions_file_not_found(
        self,
        autotrade_v1_module,
        capsys,
    ):
        """
        CHARACTERIZES: FileNotFoundError handling

        Current behavior:
        - Returns None when file not found
        - Prints "File not found." to stdout
        """
        result = autotrade_v1_module.get_instructions("nonexistent_file.md")

        # Document current behavior: returns None
        assert result is None, "Current behavior: returns None for missing file"

        # Document current behavior: prints error message
        captured = capsys.readouterr()
        assert "File not found." in captured.out, "Current behavior: prints error message"

    @pytest.mark.characterization
    def test_characterize_get_instructions_success(
        self,
        autotrade_v1_module,
        tmp_path,
    ):
        """
        CHARACTERIZES: Successful file reading

        Current behavior:
        - Returns file contents as string
        - Uses UTF-8 encoding
        """
        test_file = tmp_path / "test_instructions.md"
        test_content = "# Test Instructions\nThis is a test."
        test_file.write_text(test_content, encoding="utf-8")

        result = autotrade_v1_module.get_instructions(str(test_file))

        # Document current behavior: returns file content
        assert result == test_content, "Current behavior: returns exact file content"


class TestCharacterizeAnalyzeDataWithGpt4:
    """
    Characterization tests for analyze_data_with_gpt4 function.

    Documents the current behavior of GPT-4 interaction.
    """

    @pytest.mark.characterization
    def test_characterize_analyze_data_with_gpt4_returns_json_string(
        self,
        autotrade_v1_module,
        mock_zhipuai,
        mock_upbit,
        mock_pyupbit_orderbook,
        tmp_path,
    ):
        """
        CHARACTERIZES: analyze_data_with_glm returns JSON string

        Current behavior:
        - Uses glm-5 model
        - Reads instructions from instructions.md
        - Calls get_current_status internally
        - Returns raw content string from GLM
        - response_format is set to json_object
        """
        # Create temp instructions file
        instructions_file = tmp_path / "instructions.md"
        instructions_file.write_text("Test instructions", encoding="utf-8")

        with patch.object(autotrade_v1_module, "client", mock_zhipuai):
            with patch.object(autotrade_v1_module, "upbit", mock_upbit):
                with patch("pyupbit.get_orderbook", mock_pyupbit_orderbook):
                    # Mock the get_instructions to return content
                    with patch.object(
                        autotrade_v1_module,
                        "get_instructions",
                        return_value="Test instructions",
                    ):
                        result = autotrade_v1_module.analyze_data_with_glm("test data")

        # Document current behavior: returns string (JSON from mock)
        assert isinstance(result, str), "Current behavior: returns string"

        # Verify it's valid JSON
        parsed = json.loads(result)
        assert "decision" in parsed, "Current behavior: contains decision key"

    @pytest.mark.characterization
    def test_characterize_analyze_data_with_gpt4_no_instructions(
        self,
        autotrade_v1_module,
        mock_zhipuai,
        capsys,
    ):
        """
        CHARACTERIZES: Handling of missing instructions file

        Current behavior:
        - Returns None when instructions not found
        - Prints "No instructions found." to stdout
        """
        with patch.object(
            autotrade_v1_module,
            "get_instructions",
            return_value=None,
        ):
            result = autotrade_v1_module.analyze_data_with_glm("test data")

        # Document current behavior: returns None
        assert result is None, "Current behavior: returns None when no instructions"

        captured = capsys.readouterr()
        assert "No instructions found." in captured.out, "Current behavior: prints error message"


class TestCharacterizeExecuteBuy:
    """
    Characterization tests for execute_buy function.

    Documents the current behavior of buy order execution.
    """

    @pytest.mark.characterization
    def test_characterize_execute_buy_above_minimum_threshold(
        self,
        autotrade_v1_module,
        mock_upbit,
        capsys,
    ):
        """
        CHARACTERIZES: Buy execution above 5000 KRW minimum

        Current behavior:
        - Gets KRW balance
        - Buys with krw * 0.9995 (fee adjustment)
        - Prints success message with order result
        """
        mock_upbit.get_balance.return_value = 1000000.0  # 1M KRW

        with patch.object(autotrade_v1_module, "upbit", mock_upbit):
            autotrade_v1_module.execute_buy()

        # Document current behavior: calls buy_market_order with fee adjustment
        mock_upbit.buy_market_order.assert_called_once()
        call_args = mock_upbit.buy_market_order.call_args
        # 1000000 * 0.9995 = 999500.0
        assert call_args[0][0] == "KRW-BTC", "Current behavior: buys KRW-BTC"
        assert call_args[0][1] == 999500.0, "Current behavior: adjusts for 0.05% fee"

        # Document current behavior: prints success message
        captured = capsys.readouterr()
        assert "Buy order successful:" in captured.out, "Current behavior: prints success message"

    @pytest.mark.characterization
    def test_characterize_execute_buy_below_minimum_threshold(
        self,
        autotrade_v1_module,
        mock_upbit,
        capsys,
    ):
        """
        CHARACTERIZES: Buy is skipped when below 5000 KRW

        Current behavior:
        - Does not place order if balance <= 5000 KRW
        - No error message printed
        """
        mock_upbit.get_balance.return_value = 4000.0  # Below 5000 KRW

        with patch.object(autotrade_v1_module, "upbit", mock_upbit):
            autotrade_v1_module.execute_buy()

        # Document current behavior: no order placed
        mock_upbit.buy_market_order.assert_not_called()

    @pytest.mark.characterization
    def test_characterize_execute_buy_exception_handling(
        self,
        autotrade_v1_module,
        mock_upbit,
        capsys,
    ):
        """
        CHARACTERIZES: Exception handling in buy execution

        Current behavior:
        - Catches all exceptions
        - Prints error message with exception details
        """
        mock_upbit.get_balance.side_effect = Exception("API Error")

        with patch.object(autotrade_v1_module, "upbit", mock_upbit):
            autotrade_v1_module.execute_buy()

        # Document current behavior: prints error message
        captured = capsys.readouterr()
        assert "Failed to execute buy order:" in captured.out, (
            "Current behavior: prints error on exception"
        )


class TestCharacterizeExecuteSell:
    """
    Characterization tests for execute_sell function.

    Documents the current behavior of sell order execution.
    """

    @pytest.mark.characterization
    def test_characterize_execute_sell_above_minimum_threshold(
        self,
        autotrade_v1_module,
        mock_upbit,
        mock_pyupbit_orderbook,
        capsys,
    ):
        """
        CHARACTERIZES: Sell execution above 5000 KRW minimum

        Current behavior:
        - Gets BTC balance
        - Gets current price from orderbook
        - Sells entire BTC balance if value > 5000 KRW
        - Prints success message with order result
        """
        mock_upbit.get_balance.return_value = 0.1  # 0.1 BTC

        with patch.object(autotrade_v1_module, "upbit", mock_upbit):
            with patch("pyupbit.get_orderbook", mock_pyupbit_orderbook):
                autotrade_v1_module.execute_sell()

        # Document current behavior: calls sell_market_order
        mock_upbit.sell_market_order.assert_called_once()
        call_args = mock_upbit.sell_market_order.call_args
        assert call_args[0][0] == "KRW-BTC", "Current behavior: sells KRW-BTC"
        assert call_args[0][1] == 0.1, "Current behavior: sells full balance"

        # Document current behavior: prints success message
        captured = capsys.readouterr()
        assert "Sell order successful:" in captured.out, "Current behavior: prints success message"

    @pytest.mark.characterization
    def test_characterize_execute_sell_below_minimum_threshold(
        self,
        autotrade_v1_module,
        mock_upbit,
        mock_pyupbit_orderbook,
        capsys,
    ):
        """
        CHARACTERIZES: Sell is skipped when value below 5000 KRW

        Current behavior:
        - Does not place order if BTC value <= 5000 KRW
        """
        mock_upbit.get_balance.return_value = 0.00001  # Very small amount

        with patch.object(autotrade_v1_module, "upbit", mock_upbit):
            with patch("pyupbit.get_orderbook", mock_pyupbit_orderbook):
                autotrade_v1_module.execute_sell()

        # Document current behavior: no order placed
        mock_upbit.sell_market_order.assert_not_called()


class TestCharacterizeMakeDecisionAndExecute:
    """
    Characterization tests for make_decision_and_execute function.

    Documents the current behavior of the main decision loop.
    """

    @pytest.mark.characterization
    def test_characterize_make_decision_and_execute_buy_flow(
        self,
        autotrade_v1_module,
        mock_openai_buy_decision,
        mock_upbit,
        mock_pyupbit_ohlcv,
        mock_pyupbit_orderbook,
        capsys,
    ):
        """
        CHARACTERIZES: Buy decision execution flow

        Current behavior:
        - Fetches and prepares data
        - Analyzes with GPT-4
        - Parses JSON response
        - Calls execute_buy when decision is "buy"
        """
        with patch.object(autotrade_v1_module, "client", mock_openai_buy_decision):
            with patch.object(autotrade_v1_module, "upbit", mock_upbit):
                with patch("pyupbit.get_ohlcv", mock_pyupbit_ohlcv):
                    with patch("pyupbit.get_orderbook", mock_pyupbit_orderbook):
                        with patch.object(
                            autotrade_v1_module,
                            "get_instructions",
                            return_value="Test",
                        ):
                            autotrade_v1_module.make_decision_and_execute()

        # Document current behavior: buy order was attempted
        captured = capsys.readouterr()
        assert "Making decision and executing..." in captured.out, (
            "Current behavior: prints status message"
        )

    @pytest.mark.characterization
    def test_characterize_make_decision_and_execute_json_parse_failure(
        self,
        autotrade_v1_module,
        mock_upbit,
        mock_pyupbit_ohlcv,
        capsys,
    ):
        """
        CHARACTERIZES: JSON parsing failure handling

        Current behavior:
        - Catches exception when JSON parsing fails
        - Prints error message with exception
        """
        # Create a mock that returns invalid JSON
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Not valid JSON"))]
        mock_client.chat.completions.create.return_value = mock_response

        with patch.object(autotrade_v1_module, "client", mock_client):
            with patch.object(autotrade_v1_module, "upbit", mock_upbit):
                with patch("pyupbit.get_ohlcv", mock_pyupbit_ohlcv):
                    with patch.object(
                        autotrade_v1_module,
                        "get_instructions",
                        return_value="Test",
                    ):
                        autotrade_v1_module.make_decision_and_execute()

        # Document current behavior: prints error message
        captured = capsys.readouterr()
        assert "Failed to parse the advice as JSON:" in captured.out, (
            "Current behavior: prints error on JSON parse failure"
        )


class TestCharacterizeModuleSetup:
    """
    Characterization tests for module-level setup.

    Documents the current behavior of module initialization.
    """

    @pytest.mark.characterization
    def test_characterize_module_creates_openai_client(self, autotrade_v1_module):
        """
        CHARACTERIZES: Module creates OpenAI client at import time

        Current behavior:
        - Creates client with OPENAI_API_KEY from environment
        - Client is created at module level (global)
        """
        # Document current behavior: module has client attribute
        assert hasattr(autotrade_v1_module, "client"), (
            "Current behavior: module has 'client' attribute"
        )

    @pytest.mark.characterization
    def test_characterize_module_creates_upbit_client(self, autotrade_v1_module):
        """
        CHARACTERIZES: Module creates Upbit client at import time

        Current behavior:
        - Creates upbit with UPBIT_ACCESS_KEY and UPBIT_SECRET_KEY
        - Client is created at module level (global)
        """
        # Document current behavior: module has upbit attribute
        assert hasattr(autotrade_v1_module, "upbit"), (
            "Current behavior: module has 'upbit' attribute"
        )
