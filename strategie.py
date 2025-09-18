import pandas as pd

def semnal_tranzactionare(df: pd.DataFrame, symbol: str, config: dict) -> str:
    """
    Generează semnale BUY/SELL/HOLD pe baza indicatorilor tehnici.
    """
    try:
        # RSI
        rsi_period = config.get("RSI_Period", 7)
        delta = df["close"].diff()
        gain = (delta.where(delta > 0, 0)).rolling(rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(rsi_period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        rsi_val = rsi.iloc[-1]

        # MACD
        exp1 = df["close"].ewm(span=config.get("MACD_Fast", 12), adjust=False).mean()
        exp2 = df["close"].ewm(span=config.get("MACD_Slow", 26), adjust=False).mean()
        macd = exp1 - exp2
        signal_line = macd.ewm(span=config.get("MACD_Signal", 9), adjust=False).mean()
        macd_val = macd.iloc[-1]
        signal_val = signal_line.iloc[-1]

        # Logică simplă
        if rsi_val < config.get("RSI_OS", 30) and macd_val > signal_val:
            return "BUY"
        elif rsi_val > config.get("RSI_OB", 70) and macd_val < signal_val:
            return "SELL"
        else:
            return "HOLD"

    except Exception as e:
        return f"ERROR: {e}"
