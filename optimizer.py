import os
import pandas as pd
from dotenv import load_dotenv
from binance.client import Client
import ta
from itertools import product

# === CONFIG ===
load_dotenv()
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
SYMBOL = "BTCUSDT"

client = Client(API_KEY, API_SECRET)
client.API_URL = "https://api.binance.com/api"  # folosim date reale

# === FUNCȚIE BACKTEST ===
def run_strategy(df, rsi_period, rsi_overbought, rsi_oversold, macd_fast, macd_slow, macd_signal):
    # Calcul indicatori
    df["rsi"] = ta.momentum.RSIIndicator(df["close"], window=rsi_period).rsi()
    macd = ta.trend.MACD(df["close"], window_slow=macd_slow, window_fast=macd_fast, window_sign=macd_signal)
    df["macd"] = macd.macd()
    df["signal"] = macd.macd_signal()
    df = df.dropna()

    balance = 10000
    position = None
    entry_price = 0
    profit_trades = loss_trades = 0

    for i in range(len(df)):
        price = df["close"].iloc[i]
        rsi = df["rsi"].iloc[i]
        macd_val = df["macd"].iloc[i]
        signal_val = df["signal"].iloc[i]

        if position is None:
            if rsi < rsi_oversold and macd_val > signal_val:
                position = "LONG"
                entry_price = price
        elif position == "LONG":
            if rsi > rsi_overbought or macd_val < signal_val:
                pnl = price - entry_price
                balance += pnl
                if pnl > 0:
                    profit_trades += 1
                else:
                    loss_trades += 1
                position = None

    total_trades = profit_trades + loss_trades
    success_rate = (profit_trades / total_trades * 100) if total_trades > 0 else 0
    profit_total = balance - 10000
    return profit_total, success_rate, total_trades

# === DESCĂRCARE DATE ===
def get_historical(interval="15m", period="180 days ago UTC"):
    klines = client.get_historical_klines(SYMBOL, interval, period)
    df = pd.DataFrame(klines, columns=[
        "timestamp", "open", "high", "low", "close", "volume",
        "close_time", "qav", "num_trades", "tbbav", "tbqav", "ignore"
    ])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df["close"] = df["close"].astype(float)
    return df

# === OPTIMIZATOR ===
def optimizer():
    print("📥 Descărcăm datele istorice...")
    df = get_historical(interval="15m", period="365 days ago UTC")

    # Setăm grilele de parametri
    rsi_periods = [7, 14]
    rsi_overboughts = [65, 70, 75]
    rsi_oversolds = [25, 30, 35]
    macd_fasts = [8, 12]
    macd_slows = [20, 26]
    macd_signals = [5, 9]

    results = []
    print("⚡ Rulăm optimizatorul...")

    # Testăm toate combinațiile posibile
    for rsi_p, rsi_ob, rsi_os, mf, ms, msig in product(rsi_periods, rsi_overboughts, rsi_oversolds, macd_fasts, macd_slows, macd_signals):
        profit, success_rate, total_trades = run_strategy(df.copy(), rsi_p, rsi_ob, rsi_os, mf, ms, msig)
        results.append({
            "RSI_Period": rsi_p,
            "RSI_OB": rsi_ob,
            "RSI_OS": rsi_os,
            "MACD_Fast": mf,
            "MACD_Slow": ms,
            "MACD_Signal": msig,
            "Profit": profit,
            "Success_Rate": success_rate,
            "Total_Trades": total_trades
        })

    # Sortăm după profit descrescător
    df_results = pd.DataFrame(results)
    df_results = df_results.sort_values(by="Profit", ascending=False)
    return df_results

if __name__ == "__main__":
    df_results = optimizer()
    print("\n===== 📊 TOP 10 STRATEGII =====")
    print(df_results.head(10))
    df_results.to_csv("optimizer_results.csv", index=False)
    print("\n💾 Rezultatele au fost salvate în: optimizer_results.csv")
