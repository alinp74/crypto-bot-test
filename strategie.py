import pandas as pd
import pandas_ta as ta
from kraken_client import get_ohlc


def semnal_tranzactionare(symbol, params):
    """Generează semnal de tranzacționare pe baza RSI și MACD"""
    try:
        # Date OHLC de pe Kraken
        df = get_ohlc(symbol)

        if df is None or df.empty:
            return "HOLD", None, None, None

        # RSI
        rsi = ta.rsi(df["close"], length=params.get("RSI_Period", 7))
        last_rsi = rsi.iloc[-1]

        # MACD
        macd = ta.macd(
            df["close"],
            fast=params.get("MACD_Fast", 12),
            slow=params.get("MACD_Slow", 26),
            signal=params.get("MACD_Signal", 9),
        )
        last_macd = macd["MACD_12_26_9"].iloc[-1]
        last_signal = macd["MACDs_12_26_9"].iloc[-1]

        # Volatilitate simplă (stdev pe randamente)
        volatility = df["close"].pct_change().rolling(10).std().iloc[-1]

        # Reguli de decizie
        if last_rsi < params.get("RSI_OS", 30) and last_macd > last_signal:
            return "BUY", last_rsi, last_macd, volatility
        elif last_rsi > params.get("RSI_OB", 70) and last_macd < last_signal:
            return "SELL", last_rsi, last_macd, volatility
        else:
            return "HOLD", last_rsi, last_macd, volatility

    except Exception as e:
        print(f"[strategie] Eroare semnal {symbol}: {e}")
        return "HOLD", None, None, None
