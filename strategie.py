import pandas as pd

def semnal_tranzactionare(k, symbol: str, config: dict) -> str:
    """Generează semnal de tranzacționare (BUY/SELL/HOLD) pe baza RSI + MACD."""
    try:
        ohlc, _ = k.get_ohlc_data(symbol, interval=5, ascending=True)
        df = ohlc.copy()

        df["rsi"] = df["close"].pct_change().rolling(config["RSI_Period"]).mean()
        df["macd"] = df["close"].ewm(span=config["MACD_Fast"]).mean() - df["close"].ewm(span=config["MACD_Slow"]).mean()
        df["macd_signal"] = df["macd"].ewm(span=config["MACD_Signal"]).mean()

        latest = df.iloc[-1]

        if latest["rsi"] < config["RSI_OS"] and latest["macd"] > latest["macd_signal"]:
            return "BUY"
        elif latest["rsi"] > config["RSI_OB"] and latest["macd"] < latest["macd_signal"]:
            return "SELL"
        else:
            return "HOLD"
    except Exception:
        return "HOLD"
