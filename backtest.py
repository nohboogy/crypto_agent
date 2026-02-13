"""
backtest.py — RSI + 이동평균 전략 백테스팅 파이프라인
Upbit 공개 API에서 200일 일봉 데이터로 시뮬레이션 (실제 거래 없음)

전략:
  BUY  : RSI < 30 (과매도) — 저점 매수
  SELL : RSI > 70 (과매수) OR 데드크로스 (MA5 < MA20) — 고점 청산 / 추세 이탈
  보조 : MA5/MA20 크로스오버로 추세 확인
"""

import sys
import requests
import pandas as pd
import numpy as np
from datetime import datetime

# ─────────────────────────────────────────────────────────────────────────────
# 파라미터 (config.py와 동일)
# ─────────────────────────────────────────────────────────────────────────────
TRADING_PAIRS    = ["KRW-BTC", "KRW-ETH", "KRW-XRP"]
RSI_PERIOD       = 14
RSI_OVERSOLD     = 30   # 매수 기준
RSI_OVERBOUGHT   = 70   # 매도 기준
MA_SHORT         = 5
MA_LONG          = 20
INITIAL_CAPITAL  = 1_000_000   # 종목당 100만원


# ─────────────────────────────────────────────────────────────────────────────
# 데이터 수집
# ─────────────────────────────────────────────────────────────────────────────
def fetch_candles(market: str, count: int = 200) -> pd.DataFrame:
    url = "https://api.upbit.com/v1/candles/days"
    try:
        r = requests.get(url, params={"market": market, "count": count},
                         headers={"Accept": "application/json"}, timeout=10)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        print(f"  [ERROR] {market} 요청 실패: {e}")
        return pd.DataFrame()

    df = pd.DataFrame(data)
    df = df[["candle_date_time_kst", "opening_price",
             "high_price", "low_price", "trade_price",
             "candle_acc_trade_volume"]].copy()
    df.columns = ["date", "open", "high", "low", "close", "volume"]
    df = df.iloc[::-1].reset_index(drop=True)
    df["date"] = pd.to_datetime(df["date"])
    return df


# ─────────────────────────────────────────────────────────────────────────────
# 지표 계산
# ─────────────────────────────────────────────────────────────────────────────
def calc_rsi(series: pd.Series, period: int = RSI_PERIOD) -> pd.Series:
    delta = series.diff()
    gain  = delta.clip(lower=0).rolling(period).mean()
    loss  = (-delta.clip(upper=0)).rolling(period).mean()
    rs    = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["rsi"]   = calc_rsi(df["close"])
    df["ma5"]   = df["close"].rolling(MA_SHORT).mean()
    df["ma20"]  = df["close"].rolling(MA_LONG).mean()
    # MA 크로스 플래그
    df["golden"] = (df["ma5"].shift(1) <= df["ma20"].shift(1)) & (df["ma5"] > df["ma20"])
    df["dead"]   = (df["ma5"].shift(1) >= df["ma20"].shift(1)) & (df["ma5"] < df["ma20"])
    return df


# ─────────────────────────────────────────────────────────────────────────────
# 백테스트 엔진
# ─────────────────────────────────────────────────────────────────────────────
def run_backtest(market: str, capital: float = INITIAL_CAPITAL) -> dict:
    print(f"  [{market}] 데이터 수집 중...", end=" ", flush=True)
    df = fetch_candles(market, count=200)
    if df.empty:
        print("❌ 실패")
        return {}

    df = add_indicators(df)
    df = df.dropna(subset=["rsi", "ma5", "ma20"]).reset_index(drop=True)
    print(f"✅ {len(df)}일 로드")

    cash        = capital
    position    = 0.0      # 보유 코인 수량
    entry_price = 0.0
    entry_date  = None
    trades      = []       # 완료된 거래 (BUY→SELL 페어)
    equity      = []       # 일별 자산 가치

    for i, row in df.iterrows():
        close = row["close"]
        rsi   = row["rsi"]

        # ── 매수 신호: RSI 과매도 ─────────────────────────────────────────
        if position == 0 and pd.notna(rsi) and rsi < RSI_OVERSOLD:
            position    = cash / close
            entry_price = close
            entry_date  = row["date"]
            cash        = 0.0

        # ── 매도 신호: RSI 과매수 OR 데드크로스 (포지션 보유 시) ─────────
        elif position > 0 and pd.notna(rsi):
            sell_rsi  = rsi > RSI_OVERBOUGHT
            sell_dead = bool(row["dead"])

            if sell_rsi or sell_dead:
                exit_val = position * close
                pnl_krw  = exit_val - (position * entry_price)
                pnl_pct  = (close - entry_price) / entry_price * 100
                reason   = ("RSI 과매수" if sell_rsi else "") + \
                           (" + 데드크로스" if sell_dead and sell_rsi else
                            "데드크로스" if sell_dead else "")
                trades.append({
                    "entry_date":  entry_date,
                    "exit_date":   row["date"],
                    "entry_price": entry_price,
                    "exit_price":  close,
                    "pnl_krw":     pnl_krw,
                    "pnl_pct":     pnl_pct,
                    "reason":      reason,
                })
                cash     = exit_val
                position = 0.0

        # 자산 기록
        equity.append(cash + position * close)

    # ── 미청산 포지션 강제 청산 ───────────────────────────────────────────
    if position > 0:
        last = df.iloc[-1]
        exit_val = position * last["close"]
        pnl_krw  = exit_val - (position * entry_price)
        pnl_pct  = (last["close"] - entry_price) / entry_price * 100
        trades.append({
            "entry_date":  entry_date,
            "exit_date":   last["date"],
            "entry_price": entry_price,
            "exit_price":  last["close"],
            "pnl_krw":     pnl_krw,
            "pnl_pct":     pnl_pct,
            "reason":      "기간 종료 강제 청산",
        })
        cash = exit_val
        equity.append(cash)

    final_capital = cash
    n = len(trades)

    # ── 성과 지표 ─────────────────────────────────────────────────────────
    total_return  = (final_capital - capital) / capital * 100
    win_trades    = [t for t in trades if t["pnl_pct"] > 0]
    win_rate      = len(win_trades) / n * 100 if n else 0.0

    # 최대 낙폭 (MDD)
    eq_arr = np.array(equity)
    peak   = np.maximum.accumulate(eq_arr)
    dd     = (eq_arr - peak) / peak * 100
    mdd    = float(dd.min()) if len(dd) else 0.0

    return {
        "market":        market,
        "initial":       capital,
        "final":         final_capital,
        "total_return":  total_return,
        "n_trades":      n,
        "win_rate":      win_rate,
        "mdd":           mdd,
        "trades":        trades,
        "df_len":        len(df),
    }


# ─────────────────────────────────────────────────────────────────────────────
# 리포트 출력
# ─────────────────────────────────────────────────────────────────────────────
W = 64

def hline(ch="═"): print(ch * W)

def print_trade_table(trades):
    if not trades:
        print("    (해당 기간 거래 없음)")
        return
    print(f"  {'매수일':<12} {'매수가':>13} {'매도일':<12} {'매도가':>13} {'손익률':>8} {'손익(원)':>12}")
    print(f"  {'-'*12} {'-'*13} {'-'*12} {'-'*13} {'-'*8} {'-'*12}")
    for t in trades:
        ed  = t["entry_date"].strftime("%Y-%m-%d")
        xd  = t["exit_date"].strftime("%Y-%m-%d")
        ep  = f"{t['entry_price']:,.0f}"
        xp  = f"{t['exit_price']:,.0f}"
        pct = t["pnl_pct"]
        krw = t["pnl_krw"]
        ico = "▲" if pct > 0 else "▼"
        print(f"  {ed:<12} {ep:>13} {xd:<12} {xp:>13} {ico}{abs(pct):>6.2f}% {krw:>+12,.0f}")


def print_report(results):
    hline()
    print(f"  📊  RSI({RSI_PERIOD}) + MA({MA_SHORT}/{MA_LONG}) 전략  백테스트 결과")
    print(f"  기간: 200일 일봉  |  종목당 초기 자본: {INITIAL_CAPITAL:,}원")
    print(f"  전략: BUY RSI<{RSI_OVERSOLD}(과매도)  /  SELL RSI>{RSI_OVERBOUGHT}(과매수) or 데드크로스")
    hline()

    combined_init  = 0.0
    combined_final = 0.0

    for r in results:
        if not r: continue
        combined_init  += r["initial"]
        combined_final += r["final"]

        ret = r["total_return"]
        ico = "🟢" if ret >= 0 else "🔴"
        wins  = len([t for t in r["trades"] if t["pnl_pct"] > 0])
        loses = r["n_trades"] - wins

        print(f"\n  ┌─ {r['market']} ({'총'+str(r['df_len'])+'일 데이터'})")
        print(f"  │  총 수익률   : {ico} {ret:+.2f}%")
        print(f"  │  초기/최종   : {r['initial']:,.0f}원  →  {r['final']:,.0f}원")
        print(f"  │  거래 횟수   : {r['n_trades']}회  ({wins}승 {loses}패)")
        print(f"  │  승률        : {r['win_rate']:.1f}%")
        print(f"  │  최대 낙폭   : {r['mdd']:.2f}%")
        if wins:
            avg_w = np.mean([t["pnl_pct"] for t in r["trades"] if t["pnl_pct"] > 0])
            print(f"  │  평균 수익   : +{avg_w:.2f}%")
        if loses:
            avg_l = np.mean([t["pnl_pct"] for t in r["trades"] if t["pnl_pct"] <= 0])
            print(f"  │  평균 손실   : {avg_l:.2f}%")
        print(f"  └─ 거래 내역:")
        print_trade_table(r["trades"])

    # 합산
    combined_ret = (combined_final - combined_init) / combined_init * 100 if combined_init else 0
    ico = "🟢" if combined_ret >= 0 else "🔴"
    hline()
    print(f"\n  📌  포트폴리오 합산")
    print(f"      총 초기 자본   : {combined_init:>16,.0f} 원")
    print(f"      총 최종 자본   : {combined_final:>16,.0f} 원")
    print(f"      합산 수익률    : {ico}  {combined_ret:+.2f}%")
    hline()
    print()


# ─────────────────────────────────────────────────────────────────────────────
# 메인
# ─────────────────────────────────────────────────────────────────────────────
def main():
    print()
    hline("=")
    print(f"  🚀  Upbit 백테스트  |  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    hline("=")
    print()

    results = []
    for market in TRADING_PAIRS:
        res = run_backtest(market, capital=INITIAL_CAPITAL)
        results.append(res)

    print()
    print_report([r for r in results if r])


if __name__ == "__main__":
    main()
