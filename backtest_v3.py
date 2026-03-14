"""
instructions_v3.md 전략 백테스트 스크립트
업빗 KRW-BTC 6개월치 데이터로 수익/손실 분석
(순수 pandas/numpy로 지표 계산 - Python 3.14 호환)
"""

import warnings
from datetime import datetime, timedelta

import numpy as np
import pyupbit

warnings.filterwarnings("ignore")

# ── 설정 ────────────────────────────────────────────────
MARKET = "KRW-BTC"
INITIAL_KRW = 10_000_000  # 초기 자본 1,000만원
FEE_RATE = 0.0005  # 업빗 수수료 0.05%
BUY_RATIO = 0.40  # 매수 시 KRW의 40% 투자
SELL_RATIO = 0.50  # 매도 시 보유 BTC의 50% 매도


# ── 기술적 지표 계산 (순수 pandas) ──────────────────────


def sma(series, length):
    return series.rolling(window=length).mean()


def ema(series, length):
    return series.ewm(span=length, adjust=False).mean()


def rsi(series, length=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.ewm(com=length - 1, min_periods=length).mean()
    avg_loss = loss.ewm(com=length - 1, min_periods=length).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def macd(series, fast=12, slow=26, signal=9):
    ema_fast = ema(series, fast)
    ema_slow = ema(series, slow)
    macd_line = ema_fast - ema_slow
    signal_line = ema(macd_line, signal)
    hist = macd_line - signal_line
    return macd_line, signal_line, hist


def bollinger_bands(series, length=20, std=2):
    mid = sma(series, length)
    std_dev = series.rolling(window=length).std()
    upper = mid + std * std_dev
    lower = mid - std * std_dev
    return upper, mid, lower


def stochastic(high, low, close, k=14, d=3):
    lowest_low = low.rolling(window=k).min()
    highest_high = high.rolling(window=k).max()
    stoch_k = 100 * (close - lowest_low) / (highest_high - lowest_low)
    stoch_d = stoch_k.rolling(window=d).mean()
    return stoch_k, stoch_d


def fetch_6months_data():
    """업빗에서 6개월치 일봉 데이터 가져오기"""
    print("📡 업빗 KRW-BTC 6개월 일봉 데이터 수집 중...")

    df = pyupbit.get_ohlcv(MARKET, interval="day", count=200)

    if df is None or df.empty:
        raise ValueError("데이터 수집 실패")

    end = datetime.now()
    cutoff = end - timedelta(days=182)
    df = df[df.index >= cutoff].copy()

    print(f"✅ 수집 완료: {df.index[0].date()} ~ {df.index[-1].date()} ({len(df)}일)")
    return df


def add_indicators(df):
    """기술적 지표 추가"""
    df = df.copy()
    close = df["close"]
    high = df["high"]
    low = df["low"]

    df["SMA_10"] = sma(close, 10)
    df["EMA_10"] = ema(close, 10)
    df["RSI_14"] = rsi(close, 14)

    df["MACD"], df["MACD_signal"], df["MACD_hist"] = macd(close)

    df["BB_upper"], df["BB_mid"], df["BB_lower"] = bollinger_bands(close)

    df["STOCH_K"], df["STOCH_D"] = stochastic(high, low, close)

    return df.dropna()


def generate_signals(df):
    """
    instructions_v3 전략 신호 생성

    매수 신호:
      - EMA_10이 SMA_10을 상향 돌파 (골든크로스) + RSI < 70
      - 또는 MACD가 Signal을 상향 돌파 + EMA > SMA + RSI < 70

    매도 신호:
      - EMA_10이 SMA_10을 하향 돌파 (데드크로스)
      - RSI > 75 (과매수)
      - MACD가 Signal을 하향 돌파 + RSI > 60 (모멘텀 약화)
      - Stochastic K > 80 + RSI > 65
    """
    df = df.copy()

    df["ema_above_sma"] = df["EMA_10"] > df["SMA_10"]
    df["macd_above_sig"] = df["MACD"] > df["MACD_signal"]

    prev_ema_above = df["ema_above_sma"].shift(1).fillna(False)
    prev_macd_above = df["macd_above_sig"].shift(1).fillna(False)

    df["ema_cross_up"] = (~prev_ema_above) & df["ema_above_sma"]
    df["ema_cross_down"] = prev_ema_above & (~df["ema_above_sma"])
    df["macd_cross_up"] = (~prev_macd_above) & df["macd_above_sig"]
    df["macd_cross_down"] = prev_macd_above & (~df["macd_above_sig"])

    df["buy_signal"] = (df["ema_cross_up"] & (df["RSI_14"] < 70)) | (
        df["macd_cross_up"] & df["ema_above_sma"] & (df["RSI_14"] < 70)
    )

    df["sell_signal"] = (
        df["ema_cross_down"]
        | (df["RSI_14"] > 75)
        | (df["macd_cross_down"] & (df["RSI_14"] > 60))
        | ((df["STOCH_K"] > 80) & (df["RSI_14"] > 65))
    )

    return df


def run_backtest(df):
    """백테스트 실행"""
    krw = float(INITIAL_KRW)
    btc = 0.0
    avg_buy_price = 0.0
    trades = []

    for date, row in df.iterrows():
        price = float(row["close"])

        if row["buy_signal"] and krw > 10_000:
            invest = krw * BUY_RATIO
            btc_buy = (invest / price) * (1 - FEE_RATE)

            if btc > 0:
                avg_buy_price = (avg_buy_price * btc + price * btc_buy) / (btc + btc_buy)
            else:
                avg_buy_price = price

            btc += btc_buy
            krw -= invest

            trades.append(
                {
                    "date": date.date(),
                    "action": "BUY",
                    "price": price,
                    "invest_krw": invest,
                    "btc_amount": btc_buy,
                    "portfolio_value": krw + btc * price,
                    "rsi": float(row["RSI_14"]),
                    "ema_cross": bool(row["ema_cross_up"]),
                    "macd_cross": bool(row["macd_cross_up"]),
                }
            )

        elif row["sell_signal"] and btc > 0:
            sell_btc = btc * SELL_RATIO
            krw_recv = sell_btc * price * (1 - FEE_RATE)
            pnl_pct = (price / avg_buy_price - 1) * 100 if avg_buy_price > 0 else 0

            btc -= sell_btc
            krw += krw_recv

            trades.append(
                {
                    "date": date.date(),
                    "action": "SELL",
                    "price": price,
                    "invest_krw": krw_recv,
                    "btc_amount": sell_btc,
                    "portfolio_value": krw + btc * price,
                    "rsi": float(row["RSI_14"]),
                    "pnl_pct": pnl_pct,
                    "ema_cross": bool(row["ema_cross_down"]),
                    "macd_cross": bool(row["macd_cross_down"]),
                }
            )

    final_price = float(df["close"].iloc[-1])
    final_value = krw + btc * final_price
    return trades, krw, btc, avg_buy_price, final_price, final_value


def print_results(df, trades, krw, btc, avg_buy_price, final_price, final_value):
    """결과 출력"""
    start_price = float(df["close"].iloc[0])
    end_price = float(df["close"].iloc[-1])

    print("\n" + "=" * 65)
    print("  📊 백테스트 결과 - instructions_v3.md 전략")
    print("=" * 65)

    print(f"\n📅 분석 기간    : {df.index[0].date()} ~ {df.index[-1].date()} ({len(df)}일)")
    print(f"📈 BTC 시작가   : {start_price:>18,.0f} KRW")
    print(f"📉 BTC 종료가   : {end_price:>18,.0f} KRW")
    btc_chg = (end_price / start_price - 1) * 100
    print(f"📊 BTC 가격변화 : {btc_chg:>+17.2f}%")

    print(f"\n{'─' * 65}")
    print("  💰 포트폴리오 결과")
    print(f"{'─' * 65}")
    print(f"  초기 자본      : {INITIAL_KRW:>17,.0f} KRW")
    print(f"  최종 가치      : {final_value:>17,.0f} KRW")
    net = final_value - INITIAL_KRW
    ret = (final_value / INITIAL_KRW - 1) * 100
    sign = "+" if net >= 0 else ""
    print(f"  순 손익        : {sign}{net:>16,.0f} KRW  ({sign}{ret:.2f}%)")
    print(f"  잔여 KRW       : {krw:>17,.0f} KRW")
    print(f"  잔여 BTC       : {btc:>21.8f} BTC")
    if btc > 0 and avg_buy_price > 0:
        unrealized = (final_price / avg_buy_price - 1) * 100
        print(
            f"  BTC 평균매수가 : {avg_buy_price:>17,.0f} KRW  (미실현 {'+' if unrealized >= 0 else ''}{unrealized:.1f}%)"
        )

    # Buy & Hold 비교
    bh_btc = INITIAL_KRW / start_price * (1 - FEE_RATE)
    bh_value = bh_btc * end_price * (1 - FEE_RATE)
    bh_ret = (bh_value / INITIAL_KRW - 1) * 100
    alpha = ret - bh_ret

    print(f"\n{'─' * 65}")
    print("  📌 Buy & Hold 비교 (전액 매수 후 보유)")
    print(f"{'─' * 65}")
    print(f"  Buy&Hold 가치  : {bh_value:>17,.0f} KRW")
    print(f"  Buy&Hold 수익률: {'+' if bh_ret >= 0 else ''}{bh_ret:>15.2f}%")
    print(f"  전략 수익률    : {'+' if ret >= 0 else ''}{ret:>15.2f}%")
    print(
        f"  Alpha (초과수익): {'+' if alpha >= 0 else ''}{alpha:>14.2f}%  {'✅ 전략 우위' if alpha > 0 else '⚠ Buy&Hold 우위'}"
    )

    # 거래 통계
    buy_trades = [t for t in trades if t["action"] == "BUY"]
    sell_trades = [t for t in trades if t["action"] == "SELL"]
    total_fee = len(trades) * INITIAL_KRW * BUY_RATIO * FEE_RATE  # 추정

    print(f"\n{'─' * 65}")
    print("  🔄 거래 통계")
    print(f"{'─' * 65}")
    print(
        f"  총 거래 수     : {len(trades):>5}회 (매수 {len(buy_trades)}, 매도 {len(sell_trades)})"
    )

    if sell_trades:
        pnls = [t.get("pnl_pct", 0) for t in sell_trades if "pnl_pct" in t]
        if pnls:
            wins = [p for p in pnls if p > 0]
            losses = [p for p in pnls if p <= 0]
            print(
                f"  승률           : {len(wins)}/{len(pnls)} ({len(wins) / len(pnls) * 100:.0f}%)"
            )
            if wins:
                print(f"  평균 수익 거래 : {'+':>2}{np.mean(wins):.2f}%")
            if losses:
                print(f"  평균 손실 거래 : {np.mean(losses):.2f}%")

    # 거래 내역 테이블
    if trades:
        print(f"\n{'─' * 65}")
        print("  📋 거래 내역")
        print(f"{'─' * 65}")
        print(f"  {'날짜':12} {'행동':6} {'가격':>18} {'RSI':>7} {'포트폴리오':>16}")
        print(f"  {'-' * 12} {'-' * 6} {'-' * 18} {'-' * 7} {'-' * 16}")
        for t in trades:
            pv = t.get("portfolio_value", 0)
            print(
                f"  {t['date']!s:12} {t['action']:6} {t['price']:>18,.0f} {t['rsi']:>6.1f}  {pv:>14,.0f}"
            )

    # 월별 가격 추이
    print(f"\n{'─' * 65}")
    print("  📅 월별 BTC 가격 추이")
    print(f"{'─' * 65}")
    monthly = df.resample("ME")["close"].agg(["first", "last"])
    for d, row in monthly.iterrows():
        chg = (row["last"] / row["first"] - 1) * 100
        bars = int(min(abs(chg) / 2, 20))
        bar = ("▲" if chg > 0 else "▼") * bars
        sign = "+" if chg > 0 else ""
        print(
            f"  {d.strftime('%Y-%m')}  {row['first']:>16,.0f} → {row['last']:>16,.0f}  {sign}{chg:5.1f}%  {bar}"
        )

    # 현재 지표 상태
    latest = df.iloc[-1]
    print(f"\n{'─' * 65}")
    print(f"  📡 현재 기술 지표 ({df.index[-1].date()})")
    print(f"{'─' * 65}")
    print(f"  종가    : {latest['close']:>18,.0f} KRW")
    print(
        f"  SMA_10  : {latest['SMA_10']:>18,.0f}  {'↑ 종가 위' if latest['close'] > latest['SMA_10'] else '↓ 종가 아래'}"
    )
    print(
        f"  EMA_10  : {latest['EMA_10']:>18,.0f}  {'↑ 종가 위' if latest['close'] > latest['EMA_10'] else '↓ 종가 아래'}"
    )
    rsi_v = latest["RSI_14"]
    rsi_label = "⚠ 과매수(70+)" if rsi_v > 70 else ("⚠ 과매도(30-)" if rsi_v < 30 else "✅ 중립")
    print(f"  RSI_14  : {rsi_v:>18.2f}  {rsi_label}")
    macd_v = latest["MACD"]
    macd_s = latest["MACD_signal"]
    print(
        f"  MACD    : {macd_v:>18.2f}  {'↑ 강세' if macd_v > macd_s else '↓ 약세'} (시그널 {macd_s:.2f})"
    )
    print(f"  BB상단  : {latest['BB_upper']:>18,.0f}")
    print(f"  BB하단  : {latest['BB_lower']:>18,.0f}")
    sk = latest["STOCH_K"]
    sk_label = "⚠ 과매수(80+)" if sk > 80 else ("⚠ 과매도(20-)" if sk < 20 else "✅ 중립")
    print(f"  STOCH_K : {sk:>18.2f}  {sk_label}")

    # 현재 신호
    latest_buy = bool(df["buy_signal"].iloc[-1])
    latest_sell = bool(df["sell_signal"].iloc[-1])
    if latest_buy:
        print("\n  🟢 현재 신호: BUY")
    elif latest_sell:
        print("\n  🔴 현재 신호: SELL")
    else:
        print("\n  🟡 현재 신호: HOLD")

    print(f"\n{'=' * 65}\n")

    return {
        "initial": INITIAL_KRW,
        "final": final_value,
        "return_pct": ret,
        "bh_return": bh_ret,
        "alpha": alpha,
        "trades": len(trades),
    }


def main():
    print("🚀 instructions_v3.md 전략 백테스트 시작\n")

    df = fetch_6months_data()

    print("📐 기술적 지표 계산 중 (SMA, EMA, RSI, MACD, BB, Stoch)...")
    df = add_indicators(df)

    print("🔍 매수/매도 신호 생성 중...")
    df = generate_signals(df)
    print(f"   신호 발생: 매수 {df['buy_signal'].sum()}회, 매도 {df['sell_signal'].sum()}회")

    print("💹 백테스트 시뮬레이션 실행 중...")
    trades, krw, btc, avg_buy_price, final_price, final_value = run_backtest(df)

    print_results(df, trades, krw, btc, avg_buy_price, final_price, final_value)

    return df


if __name__ == "__main__":
    main()
