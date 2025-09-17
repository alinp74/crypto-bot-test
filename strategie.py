import pandas as pd
import talib
from kraken_client import get_ohlc


def semnal_tranzactionare(symbol, params):
    """Generează semnal BUY/SELL/HOLD pe baza RSI + MACD"""
    df = get_ohlc(symbol, interval=15, lookback=200)
    if df is None or len(df) < 35:
        return "HOLD", None, None

    df = df.rename(columns={
        "open": "open",
        "high": "high",
        "low": "low",
        "close": "close",
        "volume": "volume"
    })

    # RSI
    rsi = talib.RSI(df["close"], timeperiod=params.get("RSI_Period", 7))
    last_rsi = rsi.iloc[-1]

    # MACD
    macd, signal, hist = talib.MACD(
        df["close"],
        fastperiod=params.get("MACD_Fast", 12),
        slowperiod=params.get("MACD_Slow", 26),
        signalperiod=params.get("MACD_Signal", 9)
    )
    last_macd = macd.iloc[-1]
    last_signal = signal.iloc[-1]

    # Volatilitate (fix pentru warning Pandas)
    df = df.infer_objects(copy=False)
    volatility = df["close"].pct_change().rolling(10).std().iloc[-1]

    # Reguli decizie
    if last_rsi < params.get("RSI_OS", 30) and last_macd > last_signal:
        return "BUY", last_rsi, volatility
    elif last_rsi > params.get("RSI_OB", 70) and last_macd < last_signal:
        return "SELL", last_rsi, volatility
    else:
        return "HOLD", last_rsi, volatility
