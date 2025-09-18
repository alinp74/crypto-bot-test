import pandas as pd
import numpy as np

def semnal_tranzactionare(df):
    """
    Simplu: RSI + MACD pentru semnale.
    """
    df["close"] = pd.to_numeric(df["close"], errors="coerce")
    df["rsi"] = df["close"].rolling(7).apply(lambda x: 100 - (100 / (1 + (x.pct_change().mean() / (x.pct_change().std() + 1e-6)))), raw=False)
    df["ema12"] = df["close"].ewm(span=12, adjust=False).mean()
    df["ema26"] = df["close"].ewm(span=26, adjust=False).mean()
    df["macd"] = df["ema12"] - df["ema26"]
    df["signal"] = df["macd"].ewm(span=9, adjust=False).mean()

    latest_rsi = df["rsi"].iloc[-1]
    macd = df["macd"].iloc[-1]
    signal = df["signal"].iloc[-1]

    if latest_rsi < 30 and macd > signal:
        return "BUY"
    elif latest_rsi > 70 and macd < signal:
        return "SELL"
    else:
        return "HOLD"
