import pandas as pd
import numpy as np
from kraken_client import get_ohlc

def semnal_tranzactionare(symbol, interval=15, lookback=200):
    """
    Returnează semnalul de tranzacționare pentru un simbol:
    BUY / SELL / HOLD + scor risc + volatilitate
    """
    try:
        df = get_ohlc(symbol, interval=interval, lookback=lookback)

        if df is None or df.empty:
            return "HOLD", 50, 0.0

        # RSI
        delta = df["close"].diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = -delta.clip(upper=0).rolling(14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        # MACD
        ema12 = df["close"].ewm(span=12).mean()
        ema26 = df["close"].ewm(span=26).mean()
        macd = ema12 - ema26
        signal = macd.ewm(span=9).mean()

        # Volatilitate
        volatility = df["close"].pct_change().rolling(10).std().iloc[-1]

        # Semnal simplu
        if rsi.iloc[-1] < 30 and macd.iloc[-1] > signal.iloc[-1]:
            return "BUY", float(rsi.iloc[-1]), float(volatility)
        elif rsi.iloc[-1] > 70 and macd.iloc[-1] < signal.iloc[-1]:
            return "SELL", float(rsi.iloc[-1]), float(volatility)
        else:
            return "HOLD", float(rsi.iloc[-1]), float(volatility)

    except Exception as e:
        print(f"❌ Eroare semnal_tranzactionare pentru {symbol}: {e}")
        return "HOLD", 50, 0.0
