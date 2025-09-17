import pandas as pd
import talib
from kraken_client import get_ohlc

def semnal_tranzactionare(symbol):
    df = get_ohlc(symbol, interval=5)
    if df is None or df.empty:
        return "HOLD"

    df["volatility"] = df["close"].pct_change().rolling(10).std()
    rsi = talib.RSI(df["close"], timeperiod=7)
    macd, macdsignal, _ = talib.MACD(df["close"], fastperiod=12, slowperiod=26, signalperiod=9)

    last_rsi = rsi.iloc[-1]
    last_macd = macd.iloc[-1]
    last_signal = macdsignal.iloc[-1]

    if last_rsi < 30 and last_macd > last_signal:
        return "BUY"
    elif last_rsi > 70 and last_macd < last_signal:
        return "SELL"
    else:
        return "HOLD"
