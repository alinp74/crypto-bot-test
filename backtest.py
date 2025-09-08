import pandas as pd
import matplotlib.pyplot as plt
from binance.client import Client
import ta
import os
from dotenv import load_dotenv

# === CONFIG ===
load_dotenv()
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")

client = Client(API_KEY, API_SECRET)

SYMBOL = "BTCUSDT"
INTERVAL = Client.KLINE_INTERVAL_1HOUR
LIMIT = 1000  # aproximativ ultimele 40 de zile de date

# === DESCĂRCARE DATE ISTORICE ===
print("📥 Descărcăm datele istorice...")
klines = client.get_historical_klines(SYMBOL, INTERVAL, "90 days ago UTC")
df = pd.DataFrame(klines, columns=[
    "timestamp", "open", "high", "low", "close", "volume",
    "close_time", "qav", "num_trades", "tbbav", "tbqav", "ignore"
])

df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
df["close"] = df["close"].astype(float)

# === CALCUL INDICATORI ===
df["rsi"] = ta.momentum.RSIIndicator(df["close"], window=14).rsi()
macd = ta.trend.MACD(df["close"], window_slow=26, window_fast=12, window_sign=9)
df["macd"] = macd.macd()
df["signal"] = macd.macd_signal()

# === BACKTEST ===
initial_balance = 10000
balance = initial_balance
position = None
entry_price = 0
profit_trades = 0
loss_trades = 0
trade_history = []

for i in range(len(df)):
    price = df["close"].iloc[i]
    rsi = df["rsi"].iloc[i]
    macd_val = df["macd"].iloc[i]
    signal_val = df["signal"].iloc[i]

    if position is None:
        if rsi < 30 and macd_val > signal_val:
            position = "LONG"
            entry_price = price
            trade_history.append(("BUY", df["timestamp"].iloc[i], price))
    elif position == "LONG":
        if rsi > 70 or macd_val < signal_val:
            pnl = price - entry_price
            balance += pnl
            if pnl > 0:
                profit_trades += 1
            else:
                loss_trades += 1
            trade_history.append(("SELL", df["timestamp"].iloc[i], price))
            position = None

# === REZULTATE ===
total_trades = profit_trades + loss_trades
success_rate = (profit_trades / total_trades * 100) if total_trades > 0 else 0
profit_total = balance - initial_balance

print("===== 📊 RAPORT BACKTEST =====")
print(f"Tranzacții totale: {total_trades}")
print(f"Tranzacții profitabile: {profit_trades}")
print(f"Tranzacții pierdute: {loss_trades}")
print(f"Rata de succes: {success_rate:.2f}%")
print(f"Profit total: {profit_total:.2f} USDT")
print(f"Sold final: {balance:.2f} USDT")

# === GRAFIC ===
plt.figure(figsize=(14,7))
plt.plot(df["timestamp"], df["close"], label="Preț BTC/USDT", alpha=0.7)

for trade in trade_history:
    if trade[0] == "BUY":
        plt.scatter(trade[1], trade[2], color="green", marker="^", s=100)
    else:
        plt.scatter(trade[1], trade[2], color="red", marker="v", s=100)

plt.title("Backtesting BTC/USDT (Strategie RSI + MACD)")
plt.xlabel("Timp")
plt.ylabel("Preț")
plt.legend()
plt.grid()
plt.show()
