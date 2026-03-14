"""
Characterization tests for autotrade.py (v3 legacy code).

These tests document the current behavior of the v3 trading system.
They capture WHAT the code does, not what it SHOULD do.

Version 3 Features:
- All v2 features plus:
- Selenium-based chart screenshot capture
- GPT-4o model with vision capabilities
- Chart image analysis in decision making
- Enhanced error handling

Characterization test naming convention: test_characterize_<component>_<scenario>
"""

import base64
import importlib.util
import json
import sqlite3
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Load the legacy module dynamically
# Note: autotrade_v3.py is the actual v3 code (with selenium and GPT-4o)
V3_MODULE_PATH = Path(__file__).parent.parent.parent / "autotrade_v3.py"


@pytest.fixture
def autotrade_v3_module():
    """
    Dynamically load autotrade.py as a module for testing.
    """
    spec = importlib.util.spec_from_file_location("autotrade_v3", V3_MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules["autotrade_v3"] = module
    spec.loader.exec_module(module)
    return module


class TestCharacterizeGetCurrentBase64Image:
    """
    Characterization tests for get_current_base64_image function.

    Documents the current behavior of chart screenshot capture.
    """

    @pytest.mark.characterization
    def test_characterize_get_image_returns_base64_string(
        self,
        autotrade_v3_module,
        mock_selenium,
        tmp_path,
    ):
        """
        CHARACTERIZES: Screenshot capture returns base64 string

        Current behavior:
        - Uses Chrome in headless mode
        - Navigates to Upbit chart URL
        - Interacts with chart UI (clicks menus)
        - Saves screenshot to "screenshot.png"
        - Returns base64 encoded string
        """
        # Create a dummy screenshot file for the finally block
        screenshot_path = tmp_path / "screenshot.png"
        screenshot_path.write_bytes(b"fake image data")

        with patch("selenium.webdriver.Chrome", return_value=mock_selenium):
            # Patch the file operations in the finally block
            original_open = open

            def mock_open(file, *args, **kwargs):
                if "screenshot.png" in str(file):
                    # Return the temp file instead
                    return original_open(screenshot_path, "rb")
                return original_open(file, *args, **kwargs)

            with patch("builtins.open", side_effect=mock_open):
                result = autotrade_v3_module.get_current_base64_image()

        # Document current behavior: returns base64 string
        assert isinstance(result, str), "Current behavior: returns string"

        # Verify it's valid base64
        try:
            decoded = base64.b64decode(result)
            assert decoded == b"fake image data"
        except Exception:
            pytest.fail("Current behavior: returns valid base64 encoded data")

    @pytest.mark.characterization
    def test_characterize_get_image_chrome_options(
        self,
        autotrade_v3_module,
        capsys,
    ):
        """
        CHARACTERIZES: Chrome options configuration

        Current behavior:
        - Uses --headless mode
        - Uses --no-sandbox
        - Uses --disable-dev-shm-usage
        - Uses --disable-gpu
        - Window size: 1920x1080
        - ChromeDriver path: /usr/local/bin/chromedriver
        """
        mock_driver = MagicMock()
        mock_driver.save_screenshot.return_value = True

        with patch("selenium.webdriver.Chrome") as mock_chrome_class:
            mock_chrome_class.return_value = mock_driver

            # Create a dummy screenshot file
            with patch("builtins.open", create=True) as mock_open:
                mock_open.return_value.__enter__ = MagicMock()
                mock_open.return_value.__exit__ = MagicMock()
                mock_open.return_value.read.return_value = b"test"

                with patch.object(Path, "exists", return_value=True):
                    autotrade_v3_module.get_current_base64_image()

        # Document current behavior: Chrome was called
        mock_chrome_class.assert_called_once()
        call_kwargs = mock_chrome_class.call_args[1]

        # Check options were configured
        assert "options" in call_kwargs, "Current behavior: passes options to Chrome"

    @pytest.mark.characterization
    def test_characterize_get_image_exception_handling(
        self,
        autotrade_v3_module,
        capsys,
        tmp_path,
    ):
        """
        CHARACTERIZES: Exception handling in screenshot capture

        Current behavior:
        - Catches all exceptions
        - Prints error message
        - Returns empty string on error
        - Still attempts to read screenshot file in finally block
        """
        with patch("selenium.webdriver.Chrome") as mock_chrome:
            mock_chrome.side_effect = Exception("Chrome failed")

            # Create dummy file for finally block
            screenshot_path = tmp_path / "screenshot.png"
            screenshot_path.write_bytes(b"")

            original_open = open

            def mock_open(file, *args, **kwargs):
                if "screenshot.png" in str(file):
                    return original_open(screenshot_path, "rb")
                return original_open(file, *args, **kwargs)

            with patch("builtins.open", side_effect=mock_open):
                result = autotrade_v3_module.get_current_base64_image()

        # Document current behavior: returns empty string on error
        assert result == "", "Current behavior: returns empty string on exception"

        # Document current behavior: prints error
        captured = capsys.readouterr()
        assert "Error making current image:" in captured.out, (
            "Current behavior: prints error message"
        )

    @pytest.mark.characterization
    def test_characterize_get_image_chart_url(
        self,
        autotrade_v3_module,
    ):
        """
        CHARACTERIZES: Upbit chart URL

        Current behavior:
        - Navigates to: https://upbit.com/full_chart?code=CRIX.UPBIT.KRW-BTC
        """
        mock_driver = MagicMock()

        with patch("selenium.webdriver.Chrome", return_value=mock_driver):
            with patch("builtins.open", create=True) as mock_open:
                mock_open.return_value.__enter__ = MagicMock()
                mock_open.return_value.__exit__ = MagicMock()
                mock_open.return_value.read.return_value = b"test"

                autotrade_v3_module.get_current_base64_image()

        # Document current behavior: navigates to correct URL
        mock_driver.get.assert_called_once_with(
            "https://upbit.com/full_chart?code=CRIX.UPBIT.KRW-BTC"
        )


class TestCharacterizeAnalyzeDataWithGpt4:
    """
    Characterization tests for analyze_data_with_glm function (v3).

    Documents the current behavior of GLM-4.6v with vision capabilities.
    """

    @pytest.mark.characterization
    def test_characterize_analyze_uses_gpt4o_model(
        self,
        autotrade_v3_module,
        mock_zhipuai,
        mock_pyupbit_orderbook,
    ):
        """
        CHARACTERIZES: Uses get_default_model() for model selection

        Current behavior:
        - Model name: determined by get_default_model() (gpt-4-turbo for OpenAI, glm-4.6v for GLM)
        - Includes image in message content
        - response_format: {"type": "json_object"}
        """
        with patch.object(autotrade_v3_module, "client", mock_zhipuai):
            with patch("pyupbit.get_orderbook", mock_pyupbit_orderbook):
                with patch.object(
                    autotrade_v3_module,
                    "get_instructions",
                    return_value="Test",
                ):
                    autotrade_v3_module.analyze_data_with_glm(
                        "news", "data", "decisions", "fear_greed", "status", "base64image"
                    )

        call_kwargs = mock_zhipuai.chat.completions.create.call_args[1]

        # Document current behavior: uses get_default_model() which returns provider's default
        # When GLM_API_KEY is not set (test env), falls back to OpenAI and uses gpt-4-turbo
        assert call_kwargs["model"] == "gpt-4-turbo", (
            "Current behavior: uses gpt-4-turbo when GLM_API_KEY not available"
        )

    @pytest.mark.characterization
    def test_characterize_analyze_includes_image(
        self,
        autotrade_v3_module,
        mock_zhipuai,
        mock_pyupbit_orderbook,
    ):
        """
        CHARACTERIZES: Image is included in message content

        Current behavior:
        - User message content list contains image_url item
        - Image URL format: data:image/jpeg;base64,{image_data}
        """
        with patch.object(autotrade_v3_module, "client", mock_zhipuai):
            with patch("pyupbit.get_orderbook", mock_pyupbit_orderbook):
                with patch.object(
                    autotrade_v3_module,
                    "get_instructions",
                    return_value="Test",
                ):
                    autotrade_v3_module.analyze_data_with_glm(
                        "news", "data", "decisions", "fear_greed", "status", "testimage123"
                    )

        call_kwargs = mock_zhipuai.chat.completions.create.call_args[1]
        messages = call_kwargs["messages"]

        # Document current behavior: 2 messages (1 system + 1 user with content list)
        assert len(messages) == 2, "Current behavior: 1 system + 1 user message with content list"

        # Document current behavior: user message has content list
        last_message = messages[-1]
        assert "content" in last_message, "Current behavior: has content"
        content = last_message["content"]

        # Content should be a list with 5 text items + 1 image_url
        assert isinstance(content, list), "Current behavior: image content is list"
        assert len(content) == 6, "Current behavior: 5 text + 1 image item"
        assert "image_url" in content[-1], "Current behavior: last item has image_url key"
        assert "data:image/jpeg;base64,testimage123" in content[-1]["image_url"]["url"], (
            "Current behavior: image URL format is correct"
        )

    @pytest.mark.characterization
    def test_characterize_analyze_reads_instructions_v3(
        self,
        autotrade_v3_module,
        mock_zhipuai,
    ):
        """
        CHARACTERIZES: Reads from instructions_v3.md

        Current behavior:
        - Instructions file path: "instructions_v3.md"
        """
        with (
            patch.object(autotrade_v3_module, "client", mock_zhipuai),
            patch.object(
                autotrade_v3_module,
                "get_instructions",
            ) as mock_get_instructions,
        ):
            mock_get_instructions.return_value = "Test instructions"
            autotrade_v3_module.analyze_data_with_glm(
                "news", "data", "decisions", "fear_greed", "status", "image"
            )

        # Document current behavior: reads instructions_v3.md
        mock_get_instructions.assert_called_once_with("instructions_v3.md")

    @pytest.mark.characterization
    def test_characterize_analyze_returns_none_on_error(
        self,
        autotrade_v3_module,
        capsys,
    ):
        """
        CHARACTERIZES: Error handling returns None

        Current behavior:
        - Returns None when exception occurs
        - Prints error message with exception details
        """
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("API Error")

        with (
            patch.object(autotrade_v3_module, "client", mock_client),
            patch.object(
                autotrade_v3_module,
                "get_instructions",
                return_value="Test",
            ),
        ):
            result = autotrade_v3_module.analyze_data_with_glm(
                "news", "data", "decisions", "fear_greed", "status", "image"
            )

        # Document current behavior: returns None
        assert result is None, "Current behavior: returns None on exception"

        # Document current behavior: prints error
        captured = capsys.readouterr()
        assert "Error in analyzing data with GLM-4.6v:" in captured.out, (
            "Current behavior: prints error message"
        )


class TestCharacterizeMakeDecisionAndExecute:
    """
    Characterization tests for make_decision_and_execute function (v3).

    Documents the current behavior of the main decision loop with image.
    """

    @pytest.mark.characterization
    def test_characterize_make_decision_calls_get_image(
        self,
        autotrade_v3_module,
        mock_zhipuai,
        mock_upbit,
        mock_pyupbit_ohlcv,
        mock_pyupbit_orderbook,
        mock_serpapi,
        mock_fear_greed_api,
        initialized_test_db,
    ):
        """
        CHARACTERIZES: Screenshot capture is called

        Current behavior:
        - Calls get_current_base64_image()
        - Passes image to analyze_data_with_gpt4()
        """
        with patch.object(autotrade_v3_module, "client", mock_zhipuai):
            with patch.object(autotrade_v3_module, "upbit", mock_upbit):
                with patch("pyupbit.get_ohlcv", mock_pyupbit_ohlcv):
                    with patch("pyupbit.get_orderbook", mock_pyupbit_orderbook):
                        with patch.object(
                            autotrade_v3_module,
                            "get_instructions",
                            return_value="Test",
                        ):
                            with patch.object(
                                autotrade_v3_module,
                                "get_current_base64_image",
                                return_value="testbase64image",
                            ) as mock_get_image:
                                original_connect = sqlite3.connect

                                def mock_connect(path, *args, **kwargs):
                                    if path == "trading_decisions.sqlite":
                                        return original_connect(
                                            initialized_test_db, *args, **kwargs
                                        )
                                    return original_connect(path, *args, **kwargs)

                                with patch("sqlite3.connect", side_effect=mock_connect):
                                    autotrade_v3_module.make_decision_and_execute()

        # Document current behavior: get_current_base64_image was called
        mock_get_image.assert_called_once()

    @pytest.mark.characterization
    def test_characterize_make_decision_data_fetch_error(
        self,
        autotrade_v3_module,
        mock_upbit,
        mock_pyupbit_ohlcv,
        mock_pyupbit_orderbook,
        capsys,
    ):
        """
        CHARACTERIZES: Error handling during data fetch

        Current behavior:
        - Catches exceptions in data fetch block
        - Prints error message
        - Continues to else block (else won't execute on exception)
        """
        with patch.object(autotrade_v3_module, "upbit", mock_upbit):
            with patch("pyupbit.get_ohlcv", side_effect=Exception("Data fetch error")):
                with patch("pyupbit.get_orderbook", mock_pyupbit_orderbook):
                    autotrade_v3_module.make_decision_and_execute()

        # Document current behavior: prints error
        captured = capsys.readouterr()
        assert "Error:" in captured.out, "Current behavior: prints error message"


class TestCharacterizeModuleSetup:
    """
    Characterization tests for module-level setup (v3).
    """

    @pytest.mark.characterization
    def test_characterize_module_imports_selenium(self, autotrade_v3_module):
        """
        CHARACTERIZES: Selenium imports

        Current behavior:
        - Imports webdriver, Service, By, WebDriverWait, EC
        - Imports base64 for image encoding
        """
        # Document current behavior: selenium components available
        assert hasattr(autotrade_v3_module, "webdriver"), "Current behavior: imports webdriver"
        assert hasattr(autotrade_v3_module, "Service"), "Current behavior: imports Service"
        assert hasattr(autotrade_v3_module, "By"), "Current behavior: imports By"
        assert hasattr(autotrade_v3_module, "WebDriverWait"), (
            "Current behavior: imports WebDriverWait"
        )
        assert hasattr(autotrade_v3_module, "EC"), (
            "Current behavior: imports expected_conditions as EC"
        )

    @pytest.mark.characterization
    def test_characterize_module_imports_base64(self, autotrade_v3_module):
        """
        CHARACTERIZES: base64 import

        Current behavior:
        - Imports base64 module for image encoding
        """
        import base64

        # Document current behavior: base64 available
        assert (
            "base64" in dir(autotrade_v3_module) or base64 in vars(autotrade_v3_module).values()
        ), "Current behavior: imports base64"


class TestCharacterizeSharedFunctions:
    """
    Characterization tests for functions shared across versions.

    Documents behavior of common functions that should remain consistent.
    """

    @pytest.mark.characterization
    def test_characterize_get_current_status_shared_behavior(
        self,
        autotrade_v3_module,
        mock_upbit,
        mock_pyupbit_orderbook,
    ):
        """
        CHARACTERIZES: get_current_status same as v2

        Current behavior:
        - Returns same JSON structure as v2
        - Contains: current_time, orderbook, btc_balance, krw_balance, btc_avg_buy_price
        """
        with patch.object(autotrade_v3_module, "upbit", mock_upbit):
            with patch("pyupbit.get_orderbook", mock_pyupbit_orderbook):
                result = autotrade_v3_module.get_current_status()

        parsed = json.loads(result)

        # Document current behavior: same structure as v2
        expected_keys = {
            "current_time",
            "orderbook",
            "btc_balance",
            "krw_balance",
            "btc_avg_buy_price",
        }
        assert set(parsed.keys()) == expected_keys, "Current behavior: same keys as v2"

    @pytest.mark.characterization
    def test_characterize_fetch_and_prepare_data_shared_behavior(
        self,
        autotrade_v3_module,
        mock_pyupbit_ohlcv,
    ):
        """
        CHARACTERIZES: fetch_and_prepare_data same as v2

        Current behavior:
        - Returns double-encoded JSON (same as v1/v2)
        - Uses same technical indicators
        - Note: v3 does NOT print length (v1 prints length)
        """
        with patch("pyupbit.get_ohlcv", mock_pyupbit_ohlcv):
            result = autotrade_v3_module.fetch_and_prepare_data()

        # Document current behavior: double-encoded JSON
        inner_json = json.loads(result)
        assert isinstance(inner_json, str), "Current behavior: double-encoded JSON"

        data = json.loads(inner_json)
        assert "columns" in data, "Current behavior: uses pandas 'split' orient"

    @pytest.mark.characterization
    def test_characterize_execute_buy_shared_behavior(
        self,
        autotrade_v3_module,
        mock_upbit,
    ):
        """
        CHARACTERIZES: execute_buy same as v2

        Current behavior:
        - Same percentage-based execution
        - Same fee adjustment (0.9995)
        - Same minimum threshold (5000 KRW)
        """
        mock_upbit.get_balance.return_value = 1000000.0

        with patch.object(autotrade_v3_module, "upbit", mock_upbit):
            autotrade_v3_module.execute_buy(50)

        call_args = mock_upbit.buy_market_order.call_args
        assert call_args[0][1] == 499750.0, "Current behavior: same fee calculation as v2"

    @pytest.mark.characterization
    def test_characterize_execute_sell_shared_behavior(
        self,
        autotrade_v3_module,
        mock_upbit,
        mock_pyupbit_orderbook,
    ):
        """
        CHARACTERIZES: execute_sell same as v2

        Current behavior:
        - Same percentage-based execution
        - Same minimum threshold check (5000 KRW)
        """
        mock_upbit.get_balance.return_value = 0.1

        with patch.object(autotrade_v3_module, "upbit", mock_upbit):
            with patch("pyupbit.get_orderbook", mock_pyupbit_orderbook):
                autotrade_v3_module.execute_sell(50)

        call_args = mock_upbit.sell_market_order.call_args
        assert call_args[0][1] == 0.05, "Current behavior: same percentage calculation as v2"
