"""
main.py — 크립토 자동매매 에이전트 오케스트레이터 (페이퍼 트레이딩)
"""

import time
from datetime import datetime

from config import TRADING_PAIRS, TRADE_AMOUNT_KRW
from market_data import get_market_data, get_current_price
from strategy import generate_signal
from portfolio import Portfolio


def print_banner():
    print("=" * 55)
    print("  🤖 Crypto Auto-Trading Agent (Paper Trading Mode)")
    print("  📡 Exchange: Upbit (KRW Market)")
    print("  📈 Strategy: RSI(14) + MA Crossover (5/20)")
    print(f"  🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 55)


def run_once(portfolio):
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 📡 시장 데이터 수집 중...\n")

    signals = []
    current_prices = {}

    for market in TRADING_PAIRS:
        print(f"  ▶ {market} 분석 중...")
        df = get_market_data(market)

        if df.empty:
            print(f"    ⚠️  데이터 없음, 건너뜀")
            continue

        signal_info = generate_signal(df, market)
        signals.append(signal_info)

        price = signal_info["close"]
        current_prices[market] = price

        emoji_map = {"BUY": "🟢 BUY ", "SELL": "🔴 SELL", "HOLD": "⚪ HOLD"}
        emoji = emoji_map.get(signal_info["signal"], "❔")
        rsi_str = f"RSI={signal_info['rsi']:.1f}" if signal_info["rsi"] else "RSI=N/A"
        ma_s = f"{signal_info['ma_short']:,.0f}" if signal_info["ma_short"] else "N/A"
        ma_l = f"{signal_info['ma_long']:,.0f}" if signal_info["ma_long"] else "N/A"

        print(f"    {emoji} | 현재가: {price:>12,.0f}원 | {rsi_str}")
        print(f"         | MA단기: {ma_s:>12}  MA장기: {ma_l}")
        print(f"         | 판단 근거: {signal_info['reason']}")
        print()

    print("-" * 55)
    print("  📋 신호 요약")
    print("-" * 55)
    for s in signals:
        emoji_map = {"BUY": "🟢", "SELL": "🔴", "HOLD": "⚪"}
        print(f"  {emoji_map[s['signal']]} {s['market']:<12} → {s['signal']}")

    print("\n  🔄 페이퍼 트레이드 처리 중...")
    for s in signals:
        market = s["market"]
        price = current_prices.get(market)
        if price is None:
            continue

        if s["signal"] == "BUY":
            if market not in portfolio.positions:
                portfolio.buy(market, TRADE_AMOUNT_KRW, price)
            else:
                print(f"  [SKIP] {market} 이미 보유 중")
        elif s["signal"] == "SELL":
            if market in portfolio.positions:
                portfolio.sell(market, price)
            else:
                print(f"  [SKIP] {market} 보유 포지션 없음")
        else:
            print(f"  [HOLD] {market} 관망")

    portfolio.print_status(current_prices)


def main():
    print_banner()
    portfolio = Portfolio(initial_krw=3_000_000)

    try:
        run_once(portfolio)
    except KeyboardInterrupt:
        print("\n\n⛔ 사용자가 중지했습니다.")
    except Exception as e:
        print(f"\n[ERROR] 예외 발생: {e}")
        raise

    print("\n✅ 실행 완료 (페이퍼 트레이딩 모드 — 실제 주문 없음)\n")


if __name__ == "__main__":
    main()
