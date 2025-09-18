import pandas as pd
import numpy as np

def semnal_tranzactionare(df, symbol, config):
    """
    Generează un semnal de tranzacționare pe baza datelor OHLC.
    """

    # 🛡️ Debug - verificăm tipul obiectului
    if not isinstance(df, pd.DataFrame):
        print(f"[DEBUG] ❌ semnal_tranzactionare a primit df={df} (tip {type(df)})")
        return "HOLD"

    if df.empty:
        print(f"[DEBUG] ❌ semnal_tranzactionare: DataFrame gol pentru {symbol}")
        return "HOLD"

    try:
        # Asigurăm că avem coloana 'close'
        if "close" not in df.columns:
            print(f"[DEBUG] ❌ Lipsă coloană 'close' în df pentru {symbol}, coloane={df.columns}")
            return "HOLD"

        # Calcul RSI
        period = config.get("RSI_Period", 7)
        delta = df["close"].diff()
        gain = (delta.where(delta > 0, 0)).rolling(period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
        rs = gain / loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))
        rsi_val = rsi.iloc[-1]

        # Calcul MACD
        exp1 = df["close"].ewm(span=config.get("MACD_Fast", 12), adjust=False).mean()
        exp2 = df["close"].ewm(span=config.get("MACD_Slow", 26), adjust=False).mean()
        macd = exp1 - exp2
        signal = macd.ewm(span=config.get("MACD_Signal", 9), adjust=False).mean()
        macd_val = macd.iloc[-1]
        signal_val = signal.iloc[-1]

        # Logică semnal
        if rsi_val < config.get("RSI_OS", 30) and macd_val > signal_val:
            return "BUY"
        elif rsi_val > config.get("RSI_OB", 70) and macd_val < signal_val:
            return "SELL"
        else:
            return "HOLD"

    except Exception as e:
        print(f"[DEBUG] ❌ Eroare semnal_tranzactionare pentru {symbol}: {e}")
        return "HOLD"
