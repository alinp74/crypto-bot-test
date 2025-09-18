import pandas as pd
import numpy as np


def semnal_tranzactionare(df: pd.DataFrame, params: dict) -> str:
    """
    Generează semnal de tranzacționare (BUY / SELL / HOLD) pe baza indicatorilor tehnici.
    Folosește RSI, MACD și volatilitatea.
    """

    try:
        close = df["close"].astype(float)

        # RSI
        rsi = talib.RSI(close, timeperiod=params.get("RSI_Period", 7))
        rsi_last = rsi.iloc[-1]

        # MACD
        macd, macdsignal, macdhist = talib.MACD(
            close,
            fastperiod=params.get("MACD_Fast", 12),
            slowperiod=params.get("MACD_Slow", 26),
            signalperiod=params.get("MACD_Signal", 9),
        )
        macd_last = macd.iloc[-1]
        macdsignal_last = macdsignal.iloc[-1]

        # Volatilitate (std dev pe 10 perioade)
        volatility = close.pct_change().rolling(10).std().iloc[-1]

        # === LOGICA SEMNAL ===
        if rsi_last < params.get("RSI_OS", 30) and macd_last > macdsignal_last:
            return "BUY"
        elif rsi_last > params.get("RSI_OB", 70) and macd_last < macdsignal_last:
            return "SELL"
        else:
            return "HOLD"

    except Exception as e:
        print(f"[strategie] Eroare semnal_tranzactionare: {e}")
        return "HOLD"
