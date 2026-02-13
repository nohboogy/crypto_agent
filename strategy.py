"""
strategy.py — RSI + 이동평균 크로스오버 전략
"""

import pandas as pd
from config import RSI_OVERSOLD, RSI_OVERBOUGHT


def check_ma_crossover(df: pd.DataFrame) -> tuple[bool, bool]:
    """
    골든크로스(단기MA가 장기MA를 상향 돌파) / 데드크로스(하향 돌파) 감지.
    최근 2개 봉을 비교하여 크로스 여부 판단.
    
    Returns:
        (golden_cross, dead_cross)
    """
    if len(df) < 2:
        return False, False

    prev = df.iloc[-2]
    curr = df.iloc[-1]

    # NaN 체크
    if any(pd.isna([prev["ma_short"], prev["ma_long"],
                    curr["ma_short"], curr["ma_long"]])):
        return False, False

    # 골든크로스: 이전 봉에서 단기 < 장기, 현재 봉에서 단기 >= 장기
    golden_cross = (prev["ma_short"] < prev["ma_long"]) and (curr["ma_short"] >= curr["ma_long"])
    # 데드크로스: 이전 봉에서 단기 > 장기, 현재 봉에서 단기 <= 장기
    dead_cross = (prev["ma_short"] > prev["ma_long"]) and (curr["ma_short"] <= curr["ma_long"])

    return golden_cross, dead_cross


def generate_signal(df: pd.DataFrame, market: str = "") -> dict:
    """
    RSI + MA 크로스오버 기반 매매 신호 생성.
    
    BUY  조건: RSI < RSI_OVERSOLD AND 골든크로스
    SELL 조건: RSI > RSI_OVERBOUGHT AND 데드크로스
    HOLD: 그 외
    
    Returns:
        {
            "market": str,
            "signal": "BUY" | "SELL" | "HOLD",
            "rsi": float,
            "ma_short": float,
            "ma_long": float,
            "close": float,
            "reason": str
        }
    """
    if df.empty or len(df) < 2:
        return {
            "market": market,
            "signal": "HOLD",
            "rsi": None,
            "ma_short": None,
            "ma_long": None,
            "close": None,
            "reason": "데이터 부족",
        }

    latest = df.iloc[-1]
    rsi = latest["rsi"]
    ma_short = latest["ma_short"]
    ma_long = latest["ma_long"]
    close = latest["close"]

    golden_cross, dead_cross = check_ma_crossover(df)

    # 신호 판단
    if pd.notna(rsi) and rsi < RSI_OVERSOLD and golden_cross:
        signal = "BUY"
        reason = f"RSI={rsi:.1f} (과매도) + 골든크로스"
    elif pd.notna(rsi) and rsi > RSI_OVERBOUGHT and dead_cross:
        signal = "SELL"
        reason = f"RSI={rsi:.1f} (과매수) + 데드크로스"
    else:
        signal = "HOLD"
        parts = []
        if pd.notna(rsi):
            parts.append(f"RSI={rsi:.1f}")
        if pd.notna(ma_short) and pd.notna(ma_long):
            trend = "단기>장기(상승세)" if ma_short > ma_long else "단기<장기(하락세)"
            parts.append(trend)
        reason = ", ".join(parts) if parts else "조건 미충족"

    return {
        "market": market,
        "signal": signal,
        "rsi": round(float(rsi), 2) if pd.notna(rsi) else None,
        "ma_short": round(float(ma_short), 2) if pd.notna(ma_short) else None,
        "ma_long": round(float(ma_long), 2) if pd.notna(ma_long) else None,
        "close": float(close),
        "reason": reason,
    }
