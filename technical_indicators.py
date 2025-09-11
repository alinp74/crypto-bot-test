import pandas as pd

def calculate_rsi(prices, period=14):
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_macd(prices, fast=12, slow=26, signal=9):
    exp1 = prices.ewm(span=fast, adjust=False).mean()
    exp2 = prices.ewm(span=slow, adjust=False).mean()
    macd_line = exp1 - exp2
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    return macd_line, signal_line

def calculate_indicators(df, strategy):
    rsi = calculate_rsi(df["close"], strategy["RSI_Period"])
    macd, signal = calculate_macd(df["close"], strategy["MACD_Fast"], strategy["MACD_Slow"], strategy["MACD_Signal"])

    df["RSI"] = rsi
    df["MACD"] = macd
    df["Signal_Line"] = signal
    df["buy_signal"] = (rsi < strategy["RSI_OS"]) & (macd > signal)
    df["sell_signal"] = (rsi > strategy["RSI_OB"]) & (macd < signal)

    return df
