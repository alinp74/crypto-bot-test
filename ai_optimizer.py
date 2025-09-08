import os
import json
import numpy as np
import pandas as pd
import ta
from dotenv import load_dotenv
from binance.client import Client
from itertools import product

# === CONFIG ===
load_dotenv()
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
SYMBOL = "BTCUSDT"
CAPITAL_INITIAL = 10000

client = Client(API_KEY, API_SECRET)
client.API_URL = "https://testnet.binance.vision/api"

# === DESCĂRCARE DATE ===
def get_historical_data(period="6 months ago UTC", interval="1h"):
    klines = client.get_historical_klines(SYMBOL, interval, period)
    df = pd.DataFrame(klines, columns=[
        "timestamp", "open", "high", "low", "close", "volume",
        "close_time", "qav", "num_trades", "tbbav", "tbqav", "ignore"
    ])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df["close"] = df["close"].astype(float)
    return df

# === FUNCȚIE DE SIMULARE ===
def simulate(df, rsi_period, rsi_ob, rsi_os, macd_fast, macd_slow, macd_signal, stop_loss, take_profit):
    df["rsi"] = ta.momentum.RSIIndicator(df["close"], window=rsi_period).rsi()
    macd = ta.trend.MACD(df["close"], window_slow=macd_slow, window_fast=macd_fast, window_sign=macd_signal)
    df["macd"] = macd.macd()
    df["signal"] = macd.macd_signal()
    df.dropna(inplace=True)

    capital = CAPITAL_INITIAL
    position = None
    entry_price = None

    for i in range(1, len(df)):
        price = df["close"].iloc[i]
        rsi = df["rsi"].iloc[i]
        macd_val = df["macd"].iloc[i]
        macd_sig = df["signal"].iloc[i]

        # BUY
        if position is None and rsi < rsi_os and macd_val > macd_sig:
            position = "LONG"
            entry_price = price

        # SELL sau TAKE-PROFIT
        elif position == "LONG":
            change = (price - entry_price) / entry_price * 100
            if change <= -stop_loss:
                capital += -CAPITAL_INITIAL * (stop_loss / 100)
                position = None
            elif change >= take_profit or (rsi > rsi_ob and macd_val < macd_sig):
                capital += CAPITAL_INITIAL * (change / 100)
                position = None

    return capital

# === OPTIMIZATOR ===
def run_optimizer():
    df = get_historical_data()

    # Intervalele pe care le testăm
    rsi_periods = [7, 14, 21]
    rsi_ob_levels = [65, 70, 75]
    rsi_os_levels = [25, 30, 35]
    macd_fast_vals = [8, 12]
    macd_slow_vals = [18, 26]
    macd_signal_vals = [5, 9]
    stop_losses = [1.5, 2.0, 3.0]
    take_profits = [2.0, 3.0, 5.0]

    best_profit = -999999
    best_config = None

    for rsi_period, rsi_ob, rsi_os, macd_fast, macd_slow, macd_signal, stop_loss, take_profit in product(
        rsi_periods, rsi_ob_levels, rsi_os_levels,
        macd_fast_vals, macd_slow_vals, macd_signal_vals,
        stop_losses, take_profits
    ):
        try:
            capital = simulate(df, rsi_period, rsi_ob, rsi_os, macd_fast, macd_slow, macd_signal, stop_loss, take_profit)
            profit = capital - CAPITAL_INITIAL
            if profit > best_profit:
                best_profit = profit
                best_config = {
                    "RSI_Period": rsi_period,
                    "RSI_OB": rsi_ob,
                    "RSI_OS": rsi_os,
                    "MACD_Fast": macd_fast,
                    "MACD_Slow": macd_slow,
                    "MACD_Signal": macd_signal,
                    "Stop_Loss": stop_loss,
                    "Take_Profit": take_profit,
                    "Profit": round(profit, 2)
                }
        except Exception:
            continue

    # Salvăm strategia optimă
    if best_config:
        best_config["Updated"] = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
        with open("strategy.json", "w") as f:
            json.dump(best_config, f, indent=4)
        print(f"✅ Strategie optimizată salvată! Profit estimat: {best_config['Profit']} USDT")
    else:
        print("⚠️ Nu am găsit o strategie optimă.")

if __name__ == "__main__":
    run_optimizer()
