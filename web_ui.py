"""
AI Cryptocurrency Auto-Trading System - Streamlit Web UI

Simple web dashboard for cryptocurrency trading with:
- Real-time price charts
- Account balance display
- Holdings information
- Buy/Sell functionality
- AI-powered trading recommendations

Usage:
    streamlit run web_ui.py
"""

from __future__ import annotations

import asyncio
import sys
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from gpt_bitcoin.config.settings import get_settings
from gpt_bitcoin.dependencies.container import get_container
from gpt_bitcoin.domain import (
    CoinManager,
    Cryptocurrency,
    StrategyManager,
    TradingStrategy,
)
from gpt_bitcoin.domain.security import (
    LimitExceededError,
    PinNotSetError,
    SecurityLockedError,
    SecurityService,  # noqa: F401 (used in type hints and late evaluation)
)
from gpt_bitcoin.domain.trade_history import TradeHistoryService, TradeType
from gpt_bitcoin.domain.trading import TradingService  # noqa: F401 (used in Streamlit callbacks)
from gpt_bitcoin.infrastructure.external.mock_upbit_client import MockUpbitClient
from gpt_bitcoin.infrastructure.external.upbit_client import UpbitClient
from gpt_bitcoin.infrastructure.instructions import InstructionManager
from gpt_bitcoin.infrastructure.logging import get_logger

logger = get_logger(__name__)

# =============================================================================
# Constants
# =============================================================================

# 인터벌별 설정 (캔들 수, 캐시 TTL(초), 표시 라벨)
INTERVAL_CONFIG = {
    "minute1": {"count": 60, "ttl": 30, "label": "1분"},
    "minute30": {"count": 48, "ttl": 120, "label": "30분"},
    "minute60": {"count": 48, "ttl": 300, "label": "1시간"},
    "minute240": {"count": 42, "ttl": 600, "label": "4시간"},
    "day": {"count": 30, "ttl": 300, "label": "1일"},
}
# AI 분석 캐시 TTL (인터벌별)
AI_CACHE_TTL = {
    "minute1": 120,
    "minute30": 600,
    "minute60": 1200,
    "minute240": 3600,
    "day": 300,
}

# =============================================================================
# Page Configuration
# =============================================================================

st.set_page_config(
    page_title="AI Cryptocurrency Trading",
    page_icon="₿",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("🤖 AI Cryptocurrency Auto-Trading System")

# @MX:NOTE: testnet_mode session state 초기화 (환경 변수 TESTNET_MODE에서 읽기)
if "testnet_mode" not in st.session_state:
    settings = get_settings()
    st.session_state.testnet_mode = settings.testnet_mode

# Testnet banner (only shown in testnet mode)
if st.session_state.testnet_mode:
    st.warning(
        "🧪 **TESTNET MODE** - 가상 잔액으로 시뮬레이션 중입니다. 실제 거래가 실행되지 않습니다.",
        icon="🧪",
    )

st.markdown("---")

# =============================================================================
# Session State Initialization
# =============================================================================

if "coin_manager" not in st.session_state:
    st.session_state.coin_manager = CoinManager()
    st.session_state.strategy_manager = StrategyManager()

if "selected_coin" not in st.session_state:
    st.session_state.selected_coin = Cryptocurrency.BTC

if "selected_strategy" not in st.session_state:
    st.session_state.selected_strategy = TradingStrategy.balanced

if "auto_refresh" not in st.session_state:
    st.session_state.auto_refresh = False

if "refresh_interval" not in st.session_state:
    st.session_state.refresh_interval = 30

if "selected_interval" not in st.session_state:
    st.session_state.selected_interval = "minute60"

# Security session state - Check if PIN is already set
if "pin_verified" not in st.session_state:
    st.session_state.pin_verified = False

# Auto-verify if PIN is already set (only check once per session)
if not st.session_state.pin_verified and "pin_auto_checked" not in st.session_state:
    try:
        container = get_container()
        security_service = container.security_service()
        import asyncio

        if security_service.is_pin_set():
            st.session_state.pin_verified = True
        st.session_state.pin_auto_checked = True
    except Exception:
        st.session_state.pin_auto_checked = True  # Don't retry on error

if "show_pin_setup" not in st.session_state:
    st.session_state.show_pin_setup = False

if "pending_trade" not in st.session_state:
    st.session_state.pending_trade = None  # Stores trade details waiting for PIN confirmation

if "pin_input_attempts" not in st.session_state:
    st.session_state.pin_input_attempts = 0

# =============================================================================
# Sidebar Configuration
# =============================================================================

with st.sidebar:
    st.header("⚙️ 설정 (Settings)")

    # Testnet Mode Toggle
    st.subheader("거래 모드 (Trading Mode)")
    st.session_state.testnet_mode = st.checkbox(
        "테스트넷 모드 (Testnet)",
        value=st.session_state.testnet_mode,
        help="가상 잔액으로 시뮬레이션합니다. 실제 API 호출 없이 테스트 가능.",
    )
    if st.session_state.testnet_mode:
        st.caption("🧪 Testnet: 가상 잔액 (10M KRW)")
    else:
        st.caption("🔴 Production: 실제 거래 (주의 필요)")

    st.markdown("---")

    # Cryptocurrency Selection
    st.subheader("암호화폐 (Cryptocurrency)")
    coins = st.session_state.coin_manager.get_supported_coins()
    coin_options = {coin.value: coin for coin in coins}

    selected_coin_value = st.selectbox(
        "코인 선택",
        options=list(coin_options.keys()),
        index=list(coin_options.keys()).index(st.session_state.selected_coin.value),
    )
    st.session_state.selected_coin = coin_options[selected_coin_value]

    # Trading Strategy Selection
    st.subheader("거래 전략 (Trading Strategy)")
    strategies = [s.value for s in TradingStrategy if s != TradingStrategy.custom]

    selected_strategy_value = st.selectbox(
        "전략 선택",
        options=strategies,
        index=strategies.index(st.session_state.selected_strategy.value),
    )
    st.session_state.selected_strategy = TradingStrategy(selected_strategy_value)

    # Strategy Configuration Display
    strategy_manager = StrategyManager(strategy=st.session_state.selected_strategy)
    strategy_config = strategy_manager.get_config()

    st.markdown("**전략 파라미터:**")
    st.caption(f"최대 매수: {strategy_config.max_buy_percentage}%")
    st.caption(f"최대 매도: {strategy_config.max_sell_percentage}%")
    st.caption(f"RSI 과매도: {strategy_config.rsi_oversold}")
    st.caption(f"RSI 과매수: {strategy_config.rsi_overbought}")

    st.markdown("---")

    # AI Instruction Version Selection
    st.subheader("AI 지침 버전 (Instruction Version)")
    if "instruction_version" not in st.session_state:
        st.session_state.instruction_version = "v3"  # Default to v3

    version_options = {
        "v1": "v1 - 기본 (Basic)",
        "v2": "v2 - 멀티코인+뉴스 (Multi-coin+News)",
        "v3": "v3 - 비전 분석 (Vision Analysis) [권장]",
    }

    selected_version = st.selectbox(
        "지침 버전 선택",
        options=list(version_options.keys()),
        format_func=lambda x: version_options[x],
        index=list(version_options.keys()).index(st.session_state.instruction_version),
    )
    st.session_state.instruction_version = selected_version

    st.markdown("---")

    # Chart Interval Selector
    st.subheader("차트 인터벌")
    interval_labels = {cfg["label"]: key for key, cfg in INTERVAL_CONFIG.items()}
    current_label = INTERVAL_CONFIG.get(
        st.session_state.selected_interval, INTERVAL_CONFIG["minute60"]
    )["label"]
    selected_interval_label = st.radio(
        "인터벌 선택",
        options=list(interval_labels.keys()),
        index=list(interval_labels.keys()).index(current_label),
        horizontal=True,
        label_visibility="collapsed",
    )
    st.session_state.selected_interval = interval_labels[selected_interval_label]

    st.markdown("---")

    # Auto-refresh Settings
    st.subheader("자동 새로고침")
    st.session_state.auto_refresh = st.checkbox(
        "자동 새로고침", value=st.session_state.auto_refresh
    )
    if st.session_state.auto_refresh:
        st.session_state.refresh_interval = st.slider(
            "갱신 간격 (초)",
            min_value=10,
            max_value=300,
            value=st.session_state.refresh_interval,
            step=10,
        )

    st.markdown("---")

    # Manual Refresh Button
    if st.button("🔄 새로고침", width="stretch"):
        st.rerun()

    st.markdown("---")

    # Security Settings
    st.subheader("🔐 보안 설정 (Security)")

    # Get security service
    container = get_container()
    security_service = container.security_service()

    # Check PIN status
    try:
        is_pin_set = security_service.is_pin_set()
        pin_status = "설정됨" if is_pin_set else "미설정"
        st.caption(f"PIN 상태: {pin_status}")

        if not is_pin_set:
            if st.button("PIN 설정하기", key="setup_pin_button"):
                st.session_state.show_pin_setup = True
                st.rerun()
        else:
            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("PIN 변경", key="change_pin_button"):
                    st.session_state.show_pin_setup = True
                    st.rerun()
            with col_b:
                if st.button("보안 상태", key="security_status_button"):
                    # Show security status
                    try:
                        status = security_service.get_security_status()
                        st.info(f"""### 🔐 보안 상태
- PIN 설정: ✅ 완료
- 잠금 상태: {"🔴 잠김" if status["is_locked"] else "🟢 정상"}
- 실패 횟수: {status["failed_attempts"]}/3
- 일일 거래 한도: {status["daily_volume_limit"]:,.0f} KRW
- 일일 거래 횟수: {status["daily_trade_count"]}/{status["daily_trade_count_limit"]}
""")
                    except Exception as e:
                        st.error(f"보안 상태를 가져올 수 없습니다: {e}")

    except Exception as e:
        st.warning(f"보안 상태 확인 중 오류: {e}")

# =============================================================================
# Helper Functions
# =============================================================================


@st.cache_data(ttl=10)
def get_market_data(
    ticker: str, interval: str = "minute60", count: int = 48, testnet_mode: bool = False
):
    """Fetch market data with caching."""
    import asyncio

    async def _fetch():
        settings = get_settings()
        # @MX:NOTE: testnet_mode에 따라 클라이언트 선택
        if testnet_mode:
            client = MockUpbitClient()
        else:
            client = UpbitClient(settings)
        async with client:
            if not testnet_mode:
                ohlcv, price = await asyncio.gather(
                    client.get_ohlcv(ticker=ticker, interval=interval, count=count),
                    client.get_current_price(ticker=ticker),
                )
            else:
                ohlcv = []
                price = await client.get_current_price(ticker=ticker)
        return ohlcv, price

    return asyncio.run(_fetch())


@st.cache_data(ttl=30)
def get_account_info(testnet_mode: bool = False):
    """Fetch account information."""
    import asyncio

    async def _fetch():
        settings = get_settings()
        # @MX:NOTE: testnet_mode에 따라 클라이언트 선택
        if testnet_mode:
            client = MockUpbitClient()
        else:
            client = UpbitClient(settings)
        async with client:
            balances = await client.get_balances()
        return balances

    return asyncio.run(_fetch())


@st.cache_data(ttl=120)
def get_ai_recommendation(
    ticker: str,
    interval: str,
    strategy: TradingStrategy,
    instruction_version: str = "v3",
    testnet_mode: bool = False,
):
    """Get AI trading recommendation."""
    import asyncio

    async def _fetch():
        settings = get_settings()
        container = get_container()
        glm_client = container.glm_client()
        # @MX:NOTE: testnet_mode에 따라 클라이언트 선택
        upbit_client = MockUpbitClient() if testnet_mode else UpbitClient(settings)

        strategy_manager = StrategyManager(strategy=strategy)
        strategy_config = strategy_manager.get_config()

        # 인터벌별 OHLCV 캔들 수
        cfg = INTERVAL_CONFIG.get(interval, INTERVAL_CONFIG["day"])

        # Get market data in parallel (수정B: asyncio.gather로 병렬 호출)
        ohlcv_data, current_price = await asyncio.gather(
            upbit_client.get_ohlcv(ticker=ticker, interval=interval, count=cfg["count"]),
            upbit_client.get_current_price(ticker=ticker),
        )

        price_change = 0.0
        if len(ohlcv_data) >= 2:
            price_change = ((current_price / ohlcv_data[-1].close) - 1) * 100

        # Load instructions using InstructionManager
        instruction_manager = InstructionManager(base_path=Path(__file__).parent)

        # Determine instruction file based on version
        inst_file = "instructions.md"
        if instruction_version == "v2":
            inst_file = "instructions_v2.md"
        elif instruction_version == "v3":
            inst_file = "instructions_v3.md"

        # Build context-specific instructions
        base_instructions = instruction_manager.load(inst_file)
        if base_instructions is None:
            # Fallback to simple prompt if instructions file not found
            base_instructions = "You are a cryptocurrency trading assistant. Please respond in Korean for the reason field."

        # Prepare analysis prompt with context
        context_addition = f"""

## Current Context

Current Strategy: {strategy.value}
Max Buy Percentage: {strategy_config.max_buy_percentage}%
Max Sell Percentage: {strategy_config.max_sell_percentage}%
RSI Oversold Threshold: {strategy_config.rsi_oversold}
RSI Overbought Threshold: {strategy_config.rsi_overbought}

Cryptocurrency: {ticker}
Current Price: {current_price:,.0f} KRW

## Response Format

Respond ONLY with a JSON object wrapped in markdown code blocks:
```json
{{
    "decision": "buy" | "sell" | "hold",
    "percentage": <number 0-100>,
    "reason": "<한국어로 설명해주세요 (explain in Korean)>",
    "confidence": <number 0-1>
}}
```
Do NOT include any other text outside the JSON code block.
IMPORTANT: The 'reason' field MUST be in Korean.
"""

        system_prompt = base_instructions + context_addition

        market_summary = f"""Current Price: {current_price:,.0f} KRW
Price Change (24h): {price_change:+.2f}%
"""

        response = await glm_client.analyze_text(
            system_prompt=system_prompt,
            user_message=market_summary,
        )

        return response, current_price

    return asyncio.run(_fetch())


# =============================================================================
# Security UI Functions
# =============================================================================


def show_pin_setup_modal():
    """PIN 설정 Modal 표시"""
    container = get_container()
    security_service = container.security_service()

    st.markdown("### 🔐 PIN 설정")

    st.info("거래 보안을 위해 4자리 PIN을 설정해주세요.")

    # PIN 입력 (mask 처리)
    col1, col2 = st.columns(2)
    with col1:
        new_pin = st.text_input(
            "새 PIN (4자리 숫자)",
            type="password",
            max_chars=4,
            placeholder="****",
            key="setup_new_pin",
        )
    with col2:
        confirm_pin = st.text_input(
            "PIN 확인", type="password", max_chars=4, placeholder="****", key="setup_confirm_pin"
        )

    if st.button("PIN 설정", type="primary", key="confirm_setup_pin"):
        if not new_pin or not confirm_pin:
            st.error("PIN을 입력해주세요.")
            return

        if new_pin != confirm_pin:
            st.error("PIN이 일치하지 않습니다.")
            return

        if not new_pin.isdigit() or len(new_pin) != 4:
            st.error("PIN은 4자리 숫자여야 합니다.")
            return

        # Weak PIN check
        if new_pin in ["1234", "0000", "1111", "4321"]:
            st.warning("보안을 위해 더 강력한 PIN을 사용해주세요.")

        try:
            asyncio.run(security_service.setup_pin(new_pin))
            st.success("✅ PIN이 설정되었습니다!")
            st.session_state.pin_verified = True  # PIN 설정 후 즉시 검증 완료 상태로
            time.sleep(1)
            st.session_state.show_pin_setup = False
            st.rerun()
        except Exception as e:
            st.error(f"PIN 설정 실패: {e}")

    if st.button("취소", key="cancel_setup_pin"):
        st.session_state.show_pin_setup = False
        st.rerun()


def show_pin_verification_modal(trade_type: str, trade_details: dict):
    """
    PIN 검증 Modal 표시

    Args:
        trade_type: "buy" 또는 "sell"
        trade_details: 거래 상세 정보
    """
    container = get_container()
    security_service = container.security_service()

    st.markdown(f"### 🔐 PIN 인증 - {trade_type.upper()} 거래")

    # 거래 정보 표시
    st.info(
        f"""**거래 정보:**
- 코인: {trade_details.get("ticker", "N/A")}
- 금액: {trade_details.get("amount", 0):,.0f} KRW
- 수량: {trade_details.get("quantity", 0):.8f}"""
        if trade_type == "buy"
        else f"""**거래 정보:**
- 코인: {trade_details.get("ticker", "N/A")}
- 수량: {trade_details.get("quantity", 0):.8f}"""
    )

    st.markdown("---")

    # PIN 입력
    pin_input = st.text_input(
        "PIN 입력 (4자리)", type="password", max_chars=4, placeholder="****", key="verify_pin_input"
    )

    # 실패 횟수 표시
    if st.session_state.pin_input_attempts > 0:
        remaining_attempts = 3 - st.session_state.pin_input_attempts
        if remaining_attempts > 0:
            st.warning(f"⚠️ 남은 시도 횟수: {remaining_attempts}/3")
        else:
            st.error("🔒 PIN 인증이 잠겼습니다. 60초 후 다시 시도해주세요.")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("확인", type="primary", key="confirm_verify_pin"):
            if not pin_input:
                st.error("PIN을 입력해주세요.")
                return

            try:
                # PIN 검증
                is_valid = asyncio.run(security_service.verify_pin(pin_input))

                if is_valid:
                    st.session_state.pin_verified = True
                    st.session_state["verified_pin"] = pin_input
                    st.session_state.pin_input_attempts = 0
                    st.success("✅ PIN 인증 성공!")
                    st.session_state.pending_trade = {"verified": True, **trade_details}
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.session_state.pin_input_attempts += 1
                    remaining = 3 - st.session_state.pin_input_attempts
                    if remaining > 0:
                        st.error(f"❌ PIN이 올바르지 않습니다. 남은 시도: {remaining}")
                    else:
                        st.error("🔒 PIN 인증 실패 횟수 초과! 60초 동안 잠깁니다.")

            except PinNotSetError:
                st.error("PIN이 설정되지 않았습니다. 먼저 PIN을 설정해주세요.")
            except SecurityLockedError:
                st.error("🔒 보안이 잠겨있습니다. 잠시 후 다시 시도해주세요.")
            except Exception as e:
                st.error(f"PIN 인증 오류: {e}")

    with col2:
        if st.button("취소", key="cancel_verify_pin"):
            st.session_state.pin_verified = False
            st.session_state.pending_trade = None
            st.session_state.pin_input_attempts = 0
            st.info("거래가 취소되었습니다.")
            st.rerun()


# =============================================================================
# Main Content
# =============================================================================

# Get selected ticker
ticker = st.session_state.selected_coin.value

# Show PIN setup modal if needed
if st.session_state.show_pin_setup:
    show_pin_setup_modal()
    st.stop()  # Stop execution until PIN is set or cancelled

# Create tabs
tab1, tab2, tab3, tab4 = st.tabs(
    ["📊 차트 (Chart)", "💰 거래 (Trading)", "🤖 AI 분석 (AI Analysis)", "📋 거래 내역 (History)"]
)

with tab1:
    st.subheader(
        f"실시간 시세 차트 - {ticker} ({INTERVAL_CONFIG.get(st.session_state.selected_interval, {}).get('label', '')})"
    )

    # Fetch market data
    interval = st.session_state.selected_interval
    cfg = INTERVAL_CONFIG.get(interval, INTERVAL_CONFIG["minute60"])
    with st.spinner("시장 데이터를 가져오는 중..."):
        try:
            ohlcv_data, current_price = get_market_data(
                ticker,
                interval=interval,
                count=cfg["count"],
                testnet_mode=st.session_state.testnet_mode,
            )
        except Exception as e:
            st.error(f"시장 데이터를 가져오는데 실패했습니다: {e}")
            ohlcv_data, current_price = None, None

    if ohlcv_data and current_price:
        # Display current price
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("현재 가격", f"{current_price:,.0f} KRW")

        # Calculate 24h change
        if len(ohlcv_data) >= 2:
            prev_close = ohlcv_data[-1].close
            change = current_price - prev_close
            change_pct = (change / prev_close) * 100

            with col2:
                st.metric("변동", f"{change:+,.0f} KRW", f"{change_pct:+.2f}%")

        with col3:
            st.metric("거래량", f"{ohlcv_data[-1].volume:,.2f}")

        # Create chart
        df = pd.DataFrame(
            [
                {
                    "시간": datetime.fromtimestamp(c.timestamp / 1000),
                    "시가": c.open,
                    "고가": c.high,
                    "저가": c.low,
                    "종가": c.close,
                    "거래량": c.volume,
                }
                for c in ohlcv_data
            ]
        )
        df.set_index("시간", inplace=True)

        fig = go.Figure(
            data=[
                go.Candlestick(
                    x=df.index,
                    open=df["시가"],
                    high=df["고가"],
                    low=df["저가"],
                    close=df["종가"],
                    increasing_line_color="red",
                    decreasing_line_color="blue",
                )
            ]
        )

        fig.update_layout(
            title=f"{ticker} 가격 차트",
            xaxis_rangeslider_visible=True,
            xaxis_title="시간",
            yaxis_title="가격 (KRW)",
            height=500,
            template="plotly_dark",
        )

        st.plotly_chart(fig, width="stretch")

with tab2:
    st.subheader("계좌 정보 및 거래")

    # Fetch account info
    with st.spinner("계좌 정보를 가져오는 중..."):
        try:
            balances = get_account_info(testnet_mode=st.session_state.testnet_mode)
        except Exception as e:
            st.error(f"계좌 정보를 가져오는데 실패했습니다: {e}")
            balances = None

    if balances:
        # Filter non-zero balances
        non_zero_balances = [b for b in balances if b.balance > 0 or b.locked > 0]

        # Display KRW balance
        krw_balance = next((b for b in balances if b.currency == "KRW"), None)
        if krw_balance:
            col1, col2 = st.columns(2)
            with col1:
                st.metric("KRW 잔액", f"{krw_balance.balance:,.0f} KRW")
            with col2:
                st.metric("KRW 사용 중/잠김", f"{krw_balance.locked:,.0f} KRW")

        st.markdown("---")

        # Display cryptocurrency holdings
        if non_zero_balances:
            st.subheader("보유 자산")

            holdings_data = []
            for balance in non_zero_balances:
                if balance.currency == "KRW":
                    continue

                # Calculate current value
                coin_ticker = f"KRW-{balance.currency}"
                try:
                    coin_price = get_market_data(coin_ticker, count=1)[1]
                    current_value = balance.balance * coin_price
                except Exception:
                    current_value = 0

                holdings_data.append(
                    {
                        "통화": balance.currency,
                        "보유량": balance.balance,
                        "평균 단가": f"{balance.avg_buy_price:,.0f}"
                        if balance.avg_buy_price > 0
                        else "N/A",
                        "사용 중/잠김": balance.locked,
                        "현재 가치": f"{current_value:,.0f} KRW" if current_value > 0 else "N/A",
                    }
                )

            st.dataframe(
                holdings_data,
                hide_index=True,
            )

        # Manual Trading
        st.markdown("---")
        st.subheader("수동 거래")

        # Get services from container
        container = get_container()
        trading_service = container.trading_service()
        security_service = container.security_service()

        # Check if PIN is set
        try:
            is_pin_set = security_service.is_pin_set()
            if not is_pin_set:
                st.warning(
                    "⚠️ 거래를 시작하기 전에 PIN을 설정해주세요. 사이드바의 'PIN 설정하기' 버튼을 클릭하세요."
                )
        except Exception as e:
            st.warning(f"⚠️ 보안 상태 확인 중 오류: {e}")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### 🟢 매수 (Buy)")
            buy_amount = st.number_input(
                "매수 금액 (KRW)", min_value=5000, value=10000, step=1000, key="buy_amount"
            )

            if st.button("매수 주문", type="primary", key="buy_button"):
                # PIN verification first
                if not st.session_state.pin_verified:
                    st.session_state.pending_trade = {
                        "type": "buy",
                        "ticker": ticker,
                        "amount": buy_amount,
                        "verified": False,
                    }
                    st.rerun()

                # If PIN is verified, proceed with trade
                if (
                    st.session_state.pin_verified
                    and st.session_state.pending_trade
                    and st.session_state.pending_trade.get("verified")
                ):
                    with st.spinner("주문 검증 중..."):
                        try:
                            # Request buy order approval through security service
                            approval = asyncio.run(
                                security_service.secure_request_buy(
                                    ticker,
                                    buy_amount,
                                    pin=st.session_state.get("verified_pin", ""),
                                    session_id="web_ui",
                                )
                            )

                            # Check if approval requires high-value confirmation
                            if approval.high_value_trade and not approval.high_value_confirmed:
                                st.warning(f"⚠️ 고액 거래 ({buy_amount:,.0f} KRW)")
                                if not st.checkbox(
                                    "고액 거래임을 확인하고 실행합니다",
                                    key="confirm_high_value_buy",
                                ):
                                    st.info("거래가 취소되었습니다.")
                                    st.session_state.pin_verified = False
                                    st.session_state.pending_trade = None
                                    st.rerun()

                            # Show approval dialog
                            st.info("### 매수 주문 확인")
                            col_a, col_b = st.columns(2)
                            with col_a:
                                st.metric("주문 금액", f"{buy_amount:,.0f} KRW")
                                st.metric("예상 수량", f"{approval.estimated_quantity or 0:.8f}")
                            with col_b:
                                st.metric("예상 가격", f"{approval.estimated_price or 0:,.0f} KRW")
                                st.metric("예상 수수료", f"{approval.fee_estimate or 0:.2f} KRW")

                            # Approval button
                            if st.button("확인 및 주문 실행", type="primary", key="confirm_buy"):
                                with st.spinner("주문 실행 중..."):
                                    approval.mark_approved()
                                    result = asyncio.run(
                                        security_service.secure_execute_trade(
                                            approval, high_value_confirmed=True, session_id="web_ui"
                                        )
                                    )

                                    if result.success:
                                        st.success("### 주문 성공!")
                                        st.metric(
                                            "주문번호",
                                            result.order_id[:8] + "..."
                                            if result.order_id
                                            else "N/A",
                                        )
                                        st.metric(
                                            "실행 가격", f"{result.executed_price or 0:,.0f} KRW"
                                        )
                                        st.metric(
                                            "실행 수량", f"{result.executed_quantity or 0:.8f}"
                                        )
                                        # Reset PIN verification and rerun
                                        st.session_state.pin_verified = False
                                        st.session_state.pending_trade = None
                                        time.sleep(2)
                                        st.rerun()
                                    else:
                                        st.error("### 주문 실패")
                                        st.error(f"사유: {result.error_message}")

                            # Cancel button
                            if st.button("취소", key="cancel_buy"):
                                st.session_state.pin_verified = False
                                st.session_state.pending_trade = None
                                st.info("주문이 취소되었습니다.")
                                st.rerun()

                        except ValueError as e:
                            st.error("### 주문 오류")
                            st.error(str(e))
                            st.session_state.pin_verified = False
                            st.session_state.pending_trade = None
                        except LimitExceededError as e:
                            st.error("### 거래 한도 초과")
                            st.error(str(e))
                            st.session_state.pin_verified = False
                            st.session_state.pending_trade = None
                        except Exception as e:
                            st.error("### 오류 발생")
                            st.error(f"사유: {e!s}")
                            st.session_state.pin_verified = False
                            st.session_state.pending_trade = None

        with col2:
            st.markdown("#### 🔴 매도 (Sell)")
            sell_amount = st.number_input(
                "매도 수량", min_value=0.0, value=0.0001, step=0.0001, key="sell_amount"
            )

            if st.button("매도 주문", type="primary", key="sell_button"):
                # PIN verification first
                if not st.session_state.pin_verified:
                    st.session_state.pending_trade = {
                        "type": "sell",
                        "ticker": ticker,
                        "quantity": sell_amount,
                        "verified": False,
                    }
                    st.rerun()

                # If PIN is verified, proceed with trade
                if (
                    st.session_state.pin_verified
                    and st.session_state.pending_trade
                    and st.session_state.pending_trade.get("verified")
                ):
                    with st.spinner("주문 검증 중..."):
                        try:
                            # Request sell order approval through security service
                            approval = asyncio.run(
                                security_service.secure_request_sell(
                                    ticker,
                                    sell_amount,
                                    pin=st.session_state.get("verified_pin", ""),
                                    session_id="web_ui",
                                )
                            )

                            # Check if approval requires high-value confirmation
                            if approval.high_value_trade and not approval.high_value_confirmed:
                                st.warning("⚠️ 고액 거래")
                                if not st.checkbox(
                                    "고액 거래임을 확인하고 실행합니다",
                                    key="confirm_high_value_sell",
                                ):
                                    st.info("거래가 취소되었습니다.")
                                    st.session_state.pin_verified = False
                                    st.session_state.pending_trade = None
                                    st.rerun()

                            # Show approval dialog
                            st.info("### 매도 주문 확인")
                            col_a, col_b = st.columns(2)
                            with col_a:
                                st.metric("매도 수량", f"{sell_amount:.8f}")
                                st.metric("예상 가격", f"{approval.estimated_price or 0:,.0f} KRW")
                            with col_b:
                                st.metric(
                                    "예상 금액",
                                    f"{(approval.estimated_price or 0) * sell_amount:,.0f} KRW",
                                )
                                st.metric("예상 수수료", f"{approval.fee_estimate or 0:.2f} KRW")

                            # Approval button
                            if st.button("확인 및 주문 실행", type="primary", key="confirm_sell"):
                                with st.spinner("주문 실행 중..."):
                                    approval.mark_approved()
                                    result = asyncio.run(
                                        security_service.secure_execute_trade(
                                            approval, high_value_confirmed=True, session_id="web_ui"
                                        )
                                    )

                                    if result.success:
                                        st.success("### 주문 성공!")
                                        st.metric(
                                            "주문번호",
                                            result.order_id[:8] + "..."
                                            if result.order_id
                                            else "N/A",
                                        )
                                        st.metric(
                                            "실행 가격", f"{result.executed_price or 0:,.0f} KRW"
                                        )
                                        st.metric(
                                            "실행 수량", f"{result.executed_quantity or 0:.8f}"
                                        )
                                        # Reset PIN verification and rerun
                                        st.session_state.pin_verified = False
                                        st.session_state.pending_trade = None
                                        time.sleep(2)
                                        st.rerun()
                                    else:
                                        st.error("### 주문 실패")
                                        st.error(f"사유: {result.error_message}")

                            # Cancel button
                            if st.button("취소", key="cancel_sell"):
                                st.session_state.pin_verified = False
                                st.session_state.pending_trade = None
                                st.info("주문이 취소되었습니다.")
                                st.rerun()

                        except ValueError as e:
                            st.error("### 주문 오류")
                            st.error(str(e))
                            st.session_state.pin_verified = False
                            st.session_state.pending_trade = None
                        except LimitExceededError as e:
                            st.error("### 거래 한도 초과")
                            st.error(str(e))
                            st.session_state.pin_verified = False
                            st.session_state.pending_trade = None
                        except Exception as e:
                            st.error("### 오류 발생")
                            st.error(f"사유: {e!s}")
                            st.session_state.pin_verified = False
                            st.session_state.pending_trade = None

        # Show PIN verification modal if pending trade exists
        if st.session_state.pending_trade and not st.session_state.pending_trade.get("verified"):
            show_pin_verification_modal(
                st.session_state.pending_trade["type"], st.session_state.pending_trade
            )

with tab3:
    st.subheader("AI 거래 추천")

    # Get AI recommendation (인터벌 반영 + 캐싱)
    ai_interval = st.session_state.selected_interval
    ai_ttl = AI_CACHE_TTL.get(ai_interval, 300)
    st.caption(f"인터벌: {INTERVAL_CONFIG[ai_interval]['label']} | 캐시 유효: {ai_ttl // 60}분")
    with st.spinner("AI 분석 중..."):
        try:
            response, current_price = get_ai_recommendation(
                ticker,
                ai_interval,
                st.session_state.selected_strategy,
                st.session_state.instruction_version,
                st.session_state.testnet_mode,
            )
        except Exception as e:
            st.error(f"AI 분석에 실패했습니다: {e}")
            response = None

    if response and response.parsed:
        decision = response.parsed

        # Display recommendation with color coding
        decision_color = {
            "buy": "🟢",
            "sell": "🔴",
            "hold": "🟡",
        }.get(decision.decision, "⚪")

        st.markdown(f"### {decision_color} AI 추천: {decision.decision.upper()}")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("추천 비율", f"{decision.percentage:.1f}%")
        with col2:
            st.metric("확신도", f"{decision.confidence:.1%}")
        with col3:
            st.metric("현재 가격", f"{current_price:,.0f} KRW")

        st.markdown("---")
        st.markdown("**추천 이유:**")
        st.write(decision.reason)

        # Auto-trade button
        st.markdown("---")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("🤖 AI 추천대로 자동 거래", type="primary", width="stretch"):
                # AI 추천대로 실제 거래 실행
                try:
                    # Get security service from container
                    container = get_container()
                    security_service = container.security_service()

                    # Calculate trade amount based on recommendation
                    krw_balance = get_account_info(testnet_mode=st.session_state.testnet_mode)
                    total_krw = next((b.balance for b in krw_balance if b.currency == "KRW"), 0.0)

                    if decision.decision == "buy":
                        # Calculate buy amount (percentage of total KRW)
                        buy_amount = total_krw * (decision.percentage / 100.0)

                        # Minimum order check
                        if buy_amount < 5000:
                            st.warning(
                                f"⚠️ 최소 주문 금액 미달 (현재: {buy_amount:,.0f} KRW, 필요: 5,000 KRW)"
                            )
                        else:
                            # Request buy approval
                            with st.spinner("매수 주문 승인 요청 중..."):
                                approval = asyncio.run(
                                    security_service.secure_request_buy(
                                        ticker,
                                        buy_amount,
                                        pin=st.session_state.get("verified_pin", ""),
                                        session_id="web_ui_ai",
                                    )
                                )

                            # Display approval details and confirm
                            st.info("### 매수 주문 확인")
                            col_a, col_b = st.columns(2)
                            with col_a:
                                st.metric("주문 금액", f"{buy_amount:,.0f} KRW")
                                st.metric("예상 수량", f"{approval.estimated_quantity or 0:.8f}")
                            with col_b:
                                st.metric("예상 가격", f"{approval.estimated_price or 0:,.0f} KRW")
                                st.metric("예상 수수료", f"{approval.fee_estimate or 0:.2f} KRW")

                            # Auto-confirm after 3 seconds (for UX)
                            st.caption("⏱️ 3초 후 자동 실행됩니다...")

                            import time

                            time.sleep(3)

                            with st.spinner("주문 실행 중..."):
                                approval.mark_approved()
                                result = asyncio.run(
                                    security_service.secure_execute_trade(
                                        approval, high_value_confirmed=True, session_id="web_ui_ai"
                                    )
                                )

                            if result.success:
                                st.success("### ✅ 매수 주문 성공!")
                                col1, col2, col3 = st.columns(3)
                                with col1:
                                    st.metric(
                                        "주문번호",
                                        result.order_id[:8] + "..." if result.order_id else "N/A",
                                    )
                                with col2:
                                    st.metric("실행 가격", f"{result.executed_price or 0:,.0f} KRW")
                                with col3:
                                    st.metric("실행 수량", f"{result.executed_amount or 0:.8f}")
                                time.sleep(2)
                                st.cache_data.clear()
                                st.rerun()
                            else:
                                st.error("### ❌ 주문 실패")
                                st.error(f"사유: {result.error_message}")

                    elif decision.decision == "sell":
                        # Get coin balance for the selected ticker
                        coin = ticker.split("-")[1] if "-" in ticker else ticker
                        coin_balance = get_account_info(testnet_mode=st.session_state.testnet_mode)
                        total_coin = next(
                            (b.balance for b in coin_balance if b.currency == coin), 0.0
                        )

                        # Calculate sell quantity (percentage of total coins)
                        sell_quantity = total_coin * (decision.percentage / 100.0)

                        # Minimum check
                        if sell_quantity <= 0:
                            st.warning(f"⚠️ 보유 코인 부족 (현재: {total_coin:.8f} {coin})")
                        else:
                            # Request sell approval
                            with st.spinner("매도 주문 승인 요청 중..."):
                                approval = asyncio.run(
                                    security_service.secure_request_sell(
                                        ticker,
                                        sell_quantity,
                                        pin=st.session_state.get("verified_pin", ""),
                                        session_id="web_ui_ai",
                                    )
                                )

                            # Display approval details and confirm
                            st.info("### 매도 주문 확인")
                            col_a, col_b = st.columns(2)
                            with col_a:
                                st.metric("매도 수량", f"{sell_quantity:.8f} {coin}")
                                st.metric("예상 가격", f"{approval.estimated_price or 0:,.0f} KRW")
                            with col_b:
                                st.metric(
                                    "예상 금액",
                                    f"{(approval.estimated_price or 0) * sell_quantity:,.0f} KRW",
                                )
                                st.metric("예상 수수료", f"{approval.fee_estimate or 0:.2f} KRW")

                            # Auto-confirm after 3 seconds (for UX)
                            st.caption("⏱️ 3초 후 자동 실행됩니다...")

                            import time

                            time.sleep(3)

                            with st.spinner("주문 실행 중..."):
                                approval.mark_approved()
                                result = asyncio.run(
                                    security_service.secure_execute_trade(
                                        approval, high_value_confirmed=True, session_id="web_ui_ai"
                                    )
                                )

                            if result.success:
                                st.success("### ✅ 매도 주문 성공!")
                                col1, col2, col3 = st.columns(3)
                                with col1:
                                    st.metric(
                                        "주문번호",
                                        result.order_id[:8] + "..." if result.order_id else "N/A",
                                    )
                                with col2:
                                    st.metric("실행 가격", f"{result.executed_price or 0:,.0f} KRW")
                                with col3:
                                    st.metric("실행 수량", f"{result.executed_amount or 0:.8f}")
                                time.sleep(2)
                                st.cache_data.clear()
                                st.rerun()
                            else:
                                st.error("### ❌ 주문 실패")
                                st.error(f"사유: {result.error_message}")

                    else:  # hold
                        st.info("🟡 HOLD - AI가 거래를 권장하지 않았습니다.")

                except ValueError as e:
                    st.error("### 주문 오류")
                    st.error(str(e))
                except Exception as e:
                    st.error("### 오류 발생")
                    st.error(f"사유: {e!s}")

        with col2:
            if st.button("📊 분석 다시 받기", width="stretch"):
                st.cache_data.clear()
                st.rerun()
    else:
        st.warning("AI 추천을 가져올 수 없습니다.")

with tab4:
    st.subheader("거래 내역 (Trade History)")

    # Get container and services
    container = get_container()

    # Filters
    col1, col2, col3 = st.columns(3)

    with col1:
        # Coin filter
        filter_coin = st.selectbox(
            "코인 필터",
            options=["전체"] + [coin.value for coin in Cryptocurrency],
            format_func=lambda x: "전체" if x == "전체" else x,
            index=0,
        )

    with col2:
        # Date range filter
        filter_days = st.selectbox(
            "기간",
            options=[7, 30, 90, 180, 365, "전체"],
            format_func=lambda x: f"{x}일" if isinstance(x, int) else x,
            index=1,
        )

    with col3:
        # Trade type filter
        filter_type = st.selectbox(
            "거래 유형",
            options=["전체", "매수", "매도"],
            index=0,
        )

    # Fetch trade history
    history_service = None
    with st.spinner("거래 내역을 불러오는 중..."):
        try:
            trade_repo = container.trade_repository()
            history_service = TradeHistoryService(trade_repo)

            # Get filtered trades
            ticker_filter = None if filter_coin == "전체" else filter_coin
            from datetime import timedelta

            if filter_days == "전체":
                date_filter = None
            else:
                date_filter = (datetime.now() - timedelta(days=int(filter_days)), datetime.now())

            trades = trade_repo.get_trades(
                ticker=ticker_filter,
                start_date=date_filter[0] if date_filter else None,
                end_date=date_filter[1] if date_filter else None,
            )

            # Filter by trade type if selected
            if filter_type != "전체":
                trade_type_enum = TradeType.BUY if filter_type == "매수" else TradeType.SELL
                trades = [t for t in trades if t.trade_type == trade_type_enum]

        except Exception as e:
            st.error(f"거래 내역을 불러오는데 실패했습니다: {e}")
            trades = []

    # Display trades or show empty state
    if trades:
        # Summary metrics
        st.markdown("---")
        buy_trades = [t for t in trades if t.trade_type == TradeType.BUY]
        sell_trades = [t for t in trades if t.trade_type == TradeType.SELL]
        total_profit = (
            history_service._calculate_fifo_profit_from_trades(trades) if history_service else 0.0
        )

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("총 거래 횟수", f"{len(trades)}회")
        with col2:
            st.metric("매수 횟수", f"{len(buy_trades)}회")
        with col3:
            st.metric("매도 횟수", f"{len(sell_trades)}회")
        with col4:
            profit_color = "🟢" if total_profit >= 0 else "🔴"
            st.metric(f"{profit_color} 총 수익/손실", f"{total_profit:,.0f} KRW")

        st.markdown("---")

        # Trade history table
        st.markdown("### 거래 상세 내역")

        # Convert trades to DataFrame
        trade_data = []
        for trade in trades:
            trade_data.append(
                {
                    "시간": trade.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                    "코인": trade.ticker,
                    "유형": "매수" if trade.trade_type == TradeType.BUY else "매도",
                    "수량": f"{trade.quantity:.8f}",
                    "가격": f"{trade.price:,.0f}",
                    "금액": f"{trade.total_cost() if trade.trade_type == TradeType.BUY else trade.total_revenue():,.0f} KRW",
                }
            )

        df = pd.DataFrame(trade_data)

        # Display with color coding for trade type
        def highlight_trade_type(row):
            if row["유형"] == "매수":
                return ["background-color: rgba(0, 255, 0, 0.1)"] * len(row)
            else:
                return ["background-color: rgba(255, 0, 0, 0.1)"] * len(row)

        styled_df = df.style.apply(highlight_trade_type, axis=1)
        st.dataframe(styled_df, use_container_width=True, height=400)

    else:
        # No trades found - show empty state
        st.markdown("---")
        st.info("📭 **거래 내역이 없습니다**")
        st.markdown("""
        거래 내역이 없습니다. 첫 거래를 시작하려면:

        1. **거래 탭**으로 이동하여 매수/매도를 실행하세요
        2. 또는 **AI 분석 탭**에서 AI 추천대로 자동 거래를 실행하세요

        거래가 실행되면 여기에 거래 내역이 표시됩니다.
        """)

        # Demo data illustration
        st.markdown("---")
        st.caption("💡 **예상되는 거래 내역 모양:**")
        demo_data = {
            "시간": ["2026-03-05 14:30:00", "2026-03-05 15:20:00", "2026-03-05 16:10:00"],
            "코인": ["KRW-BTC", "KRW-BTC", "KRW-BTC"],
            "유형": ["매수", "매도", "매수"],
            "수량": ["0.00100000", "0.00100000", "0.00050000"],
            "가격": ["95,000,000", "96,000,000", "94,500,000"],
            "금액": ["95,000 KRW", "96,000 KRW", "47,250 KRW"],
        }
        st.dataframe(
            pd.DataFrame(demo_data),
            use_container_width=True,
            height=200,
        )


# =============================================================================
# Auto Refresh
# =============================================================================

if st.session_state.auto_refresh:
    time.sleep(st.session_state.refresh_interval)
    st.rerun()

# =============================================================================
# Footer
# =============================================================================

st.markdown("---")
st.caption("AI Cryptocurrency Auto-Trading System v5.0 | GLM-5/GLM-4.6V Powered")

# 시뮬레이션 모드 경고 (실제 거래 모드가 아닐 때만 표시)
if (
    st.session_state.get("testnet_mode", True)
    or st.session_state.get("trading_mode") == "simulation"
):
    st.caption("⚠️ 이 UI는 시뮬레이션/테스트넷 모드입니다. 실제 거래를 위해서는 모드를 변경하세요.")
