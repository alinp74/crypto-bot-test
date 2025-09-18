import pandas as pd


def semnal_tranzactionare(df: pd.DataFrame, symbol: str, config: dict) -> str:
    """
    Returnează BUY / SELL / HOLD pe baza RSI + MACD.
    """
    try:
        # RSI simplificat
        rsi_period = config.get("RSI_Period", 7)
        delta = df["close"].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)

        avg_gain = gain.rolling(rsi_period).mean()
        avg_loss = loss.rolling(rsi_period).mean()
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        # MACD simplificat
        exp1 = df["close"].ewm(span=config.get("MACD_Fast", 12), adjust=False).mean()
        exp2 = df["close"].ewm(span=config.get("MACD_Slow", 26), adjust=False).mean()
        macd = exp1 - exp2
        signal = macd.ewm(span=config.get("MACD_Signal", 9), adjust=False).mean()

        last_rsi = rsi.iloc[-1]
        last_macd = macd.iloc[-1]
        last_signal = signal.iloc[-1]

        if last_rsi < config.get("RSI_OS", 30) and last_macd > last_signal:
            return "BUY"
        elif last_rsi > config.get("RSI_OB", 70) and last_macd < last_signal:
            return "SELL"
        else:
            return "HOLD"

    except Exception:
        return "HOLD"
