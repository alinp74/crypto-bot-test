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
QUANTITY = 0.001  # Cantitatea de BTC pentru fiecare tranzacție

client = Client(API_KEY, API_SECRET)
client.API_URL = "https://testnet.binance.vision/api"  # << IMPORTANT! Testnet pentru siguranță

# === FUNCȚIE DESCĂRCARE DATE ===
def get_latest_data():
    klines = client.get_klines(symbol=SYMBOL, interval=Client.KLINE_INTERVAL_15MINUTE, limit=100)
    df = pd.DataFrame(klines, columns=[
        "timestamp", "open", "high", "low", "close", "volume",
        "close_time", "qav", "num_trades", "tbbav", "tbqav", "ignore"
    ])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df["close"] = df["close"].astype(float)
    return df

# === ÎNCĂRCARE STRATEGIE ===
def load_strategy():
    if os.path.exists("strategy.json"):
        with open("strategy.json", "r") as f:
            return json.load(f)
    else:
        raise Exception("⚠️ Strategie optimă lipsă! Rulează auto_optimizer.py mai întâi.")

# === SEMNAL DE TRANZACȚIE ===
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
def execute_order(order_type):
    try:
        order = client.create_order(
            symbol=SYMBOL,
            side=SIDE_BUY if order_type == "BUY" else SIDE_SELL,
            type=ORDER_TYPE_MARKET,
            quantity=QUANTITY
        )
        print(f"✅ Executat: {order_type} {QUANTITY} BTC")
        return order
    except Exception as e:
        print(f"❌ Eroare la execuție: {e}")
        return None

# === SALVARE TRANZACȚIE ===
def save_trade(order_type, price):
    trade = {
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "action": order_type,
        "price": price,
        "quantity": QUANTITY
    }
    if os.path.exists("trade_log.json"):
        with open("trade_log.json", "r") as f:
            history = json.load(f)
    else:
        history = []
    history.append(trade)
    with open("trade_log.json", "w") as f:
        json.dump(history, f, indent=4)

# === BUCLE PRINCIPAL ===
def run_bot():
    strategy = load_strategy()
    print(f"🤖 Bot pornit! Strategia curentă: {strategy}")

    while True:
        df = get_latest_data()
        signal = generate_signal(df, strategy)
        last_price = df["close"].iloc[-1]

        print(f"[{datetime.now().strftime('%H:%M:%S')}] Preț: {last_price} | Semnal: {signal}")

        if signal in ["BUY", "SELL"]:
            order = execute_order(signal)
            if order:
                save_trade(signal, last_price)

        time.sleep(15)  # verificăm la fiecare 15 secunde

if __name__ == "__main__":
    run_bot()
