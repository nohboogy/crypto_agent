"""
market_data.py — Upbit 공개 API로 실시간 캔들 데이터 수집 및 지표 계산
"""

from typing import Optional
import requests
import pandas as pd
import numpy as np
from config import RSI_PERIOD, MA_SHORT, MA_LONG


UPBIT_BASE_URL = "https://api.upbit.com/v1"


def fetch_candles(market: str, count: int = 200, unit: str = "days") -> pd.DataFrame:
    """
    Upbit 공개 API에서 캔들 데이터를 가져와 DataFrame으로 반환.
    
    Args:
        market: 마켓 코드 (e.g. "KRW-BTC")
        count: 캔들 개수 (최대 200)
        unit: "days" | "minutes" | "weeks" | "months"
    
    Returns:
        DataFrame with columns: [timestamp, open, high, low, close, volume]
    """
    if unit == "days":
        url = f"{UPBIT_BASE_URL}/candles/days"
    elif unit == "minutes":
        url = f"{UPBIT_BASE_URL}/candles/minutes/60"
    else:
        url = f"{UPBIT_BASE_URL}/candles/{unit}"

    params = {"market": market, "count": count}
    headers = {"Accept": "application/json"}

    try:
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        print(f"  [ERROR] {market} 캔들 데이터 요청 실패: {e}")
        return pd.DataFrame()

    if not data:
        print(f"  [WARN] {market} 캔들 데이터 없음")
        return pd.DataFrame()

    df = pd.DataFrame(data)
    # API 응답에 'timestamp'(unix ms) 필드가 이미 있으므로 먼저 제거 후 rename
    df = df.drop(columns=["timestamp"], errors="ignore")
    df = df.rename(columns={
        "candle_date_time_kst": "timestamp",
        "opening_price": "open",
        "high_price": "high",
        "low_price": "low",
        "trade_price": "close",
        "candle_acc_trade_volume": "volume",
    })
    df = df[["timestamp", "open", "high", "low", "close", "volume"]]
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").reset_index(drop=True)
    return df


def calculate_rsi(series: pd.Series, period: int = RSI_PERIOD) -> pd.Series:
    """
    RSI(Relative Strength Index) 계산.
    Wilder's smoothing method 사용.
    """
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi


def calculate_moving_averages(df: pd.DataFrame) -> pd.DataFrame:
    """
    단기/장기 이동평균 계산하여 DataFrame에 추가.
    """
    df = df.copy()
    df["ma_short"] = df["close"].rolling(window=MA_SHORT).mean()
    df["ma_long"] = df["close"].rolling(window=MA_LONG).mean()
    return df


def get_market_data(market: str) -> pd.DataFrame:
    """
    전체 파이프라인: 캔들 조회 → RSI + MA 계산 → 최종 DataFrame 반환.
    """
    df = fetch_candles(market, count=200)
    if df.empty:
        return df

    df["rsi"] = calculate_rsi(df["close"])
    df = calculate_moving_averages(df)
    return df


def get_current_price(market: str) -> Optional[float]:
    """현재가 조회."""
    url = f"{UPBIT_BASE_URL}/ticker"
    try:
        resp = requests.get(url, params={"markets": market}, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        return float(data[0]["trade_price"]) if data else None
    except Exception:
        return None
