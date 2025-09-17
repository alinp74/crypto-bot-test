import pandas as pd
import numpy as np
from kraken_client import get_ohlc

def calc_indicators(df):
    df["rsi"] = calc_rsi(df["close"], 14)
    df["macd"], df["signal"] = calc_macd(df["close"])
    df["volatility"] = df["close"].pct_change().rolling(10).std()
    return df

def calc_rsi(prices, period=14):
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calc_macd(prices, fast=12, slow=26, signal=9):
    ema_fast = prices.ewm(span=fast, adjust=False).mean()
    ema_slow = prices.ewm(span=slow, adjust=False).mean()
    macd = ema_fast - ema_slow
    signal_line = macd.ewm(span=signal, adjust=False).mean()
    return macd, signal_line

def semnal_tranzactionare(pair="XXBTZEUR"):
    df = get_ohlc(pair, interval=5, lookback=100)
    if df is None or len(df) < 30:
        return "HOLD"

    df = calc_indicators(df)
    rsi = df["rsi"].iloc[-1]
    macd = df["macd"].iloc[-1]
    signal = df["signal"].iloc[-1]

    if rsi < 30 and macd > signal:
        return "BUY"
    elif rsi > 70 and macd < signal:
        return "SELL"
    else:
        return "HOLD"
