import os
import json
import time
import pandas as pd
from dotenv import load_dotenv
from binance.client import Client
from binance.enums import *
import ta
from datetime import datetime

# === CONFIG ===
load_dotenv()
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")

SYMBOL = "BTCUSDT"
QUANTITY = 0.001
STOP_LOSS = 2.0        # procent pierdere maximă per tranzacție
TAKE_PROFIT = 3.0      # procent profit per tranzacție
MAX_TRADES_PER_DAY = 5
MAX_DAILY_LOSS = 50.0  # USDT

client = Client(API_KEY, API_SECRET)
client.API_URL = "https://testnet.binance.vision/api"  # Testnet pentru siguranță

# === ÎNCĂRCARE STRATEGIE ===
def load_strategy():
    if os.path.exists("strategy.json"):
        with open("strategy.json", "r") as f:
            return json.load(f)
    else:
        raise Exception("⚠️ Lipsă strategie! Rulează auto_optimizer.py.")

# === DESCĂRCARE DATE LIVE ===
def get_latest_data():
    klines = client.get_klines(symbol=SYMBOL, interval=Client.KLINE_INTERVAL_15MINUTE, limit=100)
    df = pd.DataFrame(klines, columns=[
        "timestamp", "open", "high", "low", "close", "volume",
        "close_time", "qav", "num_trades", "tbbav", "tbqav", "ignore"
    ])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df["close"] = df["close"].astype(float)
    return df

# === GENERARE SEMNAL ===
def generate_signal(df, strategy):
    df["rsi"] = ta.momentum.RSIIndicator(df["close"], window=int(strategy["RSI_Period"])).rsi()
    macd = ta.trend.MACD(
        df["close"],
        window_slow=int(strategy["MACD_Slow"]),
        window_fast=int(strategy["MACD_Fast"]),
        window_sign=int(strategy["MACD_Signal"])
    )
    df["macd"] = macd.macd()
    df["signal"] = macd.macd_signal()
    df = df.dropna()

    last_rsi = df["rsi"].iloc[-1]
    last_macd = df["macd"].iloc[-1]
    last_signal = df["signal"].iloc[-1]

    if last_rsi < float(strategy["RSI_OS"]) and last_macd > last_signal:
        return "BUY"
    elif last_rsi > float(strategy["RSI_OB"]) and last_macd < last_signal:
        return "SELL"
    return "HOLD"

# === EXECUTĂ ORDINE ===
def execute_order(order_type, price):
    try:
        order = client.create_order(
            symbol=SYMBOL,
            side=SIDE_BUY if order_type == "BUY" else SIDE_SELL,
            type=ORDER_TYPE_MARKET,
            quantity=QUANTITY
        )
        print(f"✅ Executat: {order_type} {QUANTITY} BTC la {price} USDT")
        return order
    except Exception as e:
        print(f"❌ Eroare execuție: {e}")
        return None

# === SALVARE TRANZACȚII ===
def save_trade(order_type, entry_price, exit_price=None):
    trade = {
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "action": order_type,
        "entry_price": entry_price,
        "exit_price": exit_price,
        "pnl": 0 if exit_price is None else exit_price - entry_price,
        "quantity": QUANTITY
    }
    history = []
    if os.path.exists("trade_log.json"):
        with open("trade_log.json", "r") as f:
            history = json.load(f)
    history.append(trade)
    with open("trade_log.json", "w") as f:
        json.dump(history, f, indent=4)

# === VERIFICARE LIMITĂ RISC ===
def check_risk(trades):
    today = datetime.now().strftime("%Y-%m-%d")
    daily_trades = [t for t in trades if t["time"].startswith(today)]
    total_trades = len(daily_trades)
    losses = sum(t.get("pnl", 0) for t in daily_trades if t["pnl"] < 0)

    if total_trades >= MAX_TRADES_PER_DAY:
        print("⚠️ Limită tranzacții zilnice atinsă. Bot oprit.")
        return False

    if abs(losses) >= MAX_DAILY_LOSS:
        print("🚨 Pierdere zilnică maximă atinsă! Bot oprit.")
        return False

    return True

# === BUCLE PRINCIPAL ===
def run_bot():
    strategy = load_strategy()
    print(f"🤖 Bot pornit! Strategia: {strategy}")

    while True:
        df = get_latest_data()
        signal = generate_signal(df, strategy)
        last_price = df["close"].iloc[-1]

        trades = []
        if os.path.exists("trade_log.json"):
            with open("trade_log.json", "r") as f:
                trades = json.load(f)

        # Verificăm riscul
        if not check_risk(trades):
            print("🛑 Bot oprit din cauza regulilor de risc.")
            break

        print(f"[{datetime.now().strftime('%H:%M:%S')}] Preț: {last_price} | Semnal: {signal}")

        if signal in ["BUY", "SELL"]:
            order = execute_order(signal, last_price)
            if order:
                save_trade(signal, last_price)

        time.sleep(15)  # verificăm la fiecare 15 secunde

if __name__ == "__main__":
    run_bot()
