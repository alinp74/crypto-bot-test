import os
import json
import time
import pandas as pd
from dotenv import load_dotenv
from binance.client import Client
from binance.enums import *
import ta
from datetime import datetime
from ai_risk_manager import manage_risk   # ✅ Integrare Risk Manager

# === CONFIG ===
load_dotenv()
API_KEY = os.getenv("API_KEY_MAINNET")    # Cheile API reale sau testnet
API_SECRET = os.getenv("API_SECRET_MAINNET")
SYMBOL = "BTCUSDT"

client = Client(API_KEY, API_SECRET)  # Conectare Binance Mainnet / Testnet

# === ÎNCĂRCARE STRATEGIE ===
def load_strategy():
    if os.path.exists("strategy.json"):
        with open("strategy.json", "r") as f:
            return json.load(f)
    else:
        raise Exception("⚠️ Lipsă strategie! Rulează întâi AI Optimizer.")

# === DESCĂRCARE DATE ===
def get_latest_data():
    klines = client.get_klines(symbol=SYMBOL, interval=Client.KLINE_INTERVAL_15MINUTE, limit=100)
    df = pd.DataFrame(klines, columns=[
        "timestamp", "open", "high", "low", "close", "volume",
        "close_time", "qav", "num_trades", "tbbav", "tbqav", "ignore"
    ])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df["close"] = df["close"].astype(float)
    return df

# === SEMNALE STRATEGIE ===
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
    df.dropna(inplace=True)

    last_rsi = df["rsi"].iloc[-1]
    last_macd = df["macd"].iloc[-1]
    last_signal = df["signal"].iloc[-1]

    if last_rsi < float(strategy["RSI_OS"]) and last_macd > last_signal:
        return "BUY"
    elif last_rsi > float(strategy["RSI_OB"]) and last_macd < last_signal:
        return "SELL"
    return "HOLD"

# === EXECUTĂ ORDINE ===
def execute_order(order_type, price, quantity):
    try:
        order = client.create_order(
            symbol=SYMBOL,
            side=SIDE_BUY if order_type == "BUY" else SIDE_SELL,
            type=ORDER_TYPE_MARKET,
            quantity=quantity
        )
        print(f"✅ Executat: {order_type} {quantity} BTC la {price} USDT")
        return order
    except Exception as e:
        print(f"❌ Eroare execuție: {e}")
        return None

# === SALVEAZĂ TRANZACȚIA ===
def save_trade(order_type, entry_price, exit_price=None, quantity=0):
    trade = {
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "action": order_type,
        "entry_price": entry_price,
        "exit_price": exit_price,
        "pnl": 0 if exit_price is None else round(exit_price - entry_price, 2),
        "quantity": quantity
    }
    history = []
    if os.path.exists("trade_log.json"):
        with open("trade_log.json", "r") as f:
            history = json.load(f)
    history.append(trade)
    with open("trade_log.json", "w") as f:
        json.dump(history, f, indent=4)

# === BUCLE PRINCIPAL ===
def run_bot():
    strategy = load_strategy()
    print(f"🤖 Bot AI REAL pornit! Strategia optimă: {strategy}")

    while True:
        try:
            # === Descărcăm date live
            df = get_latest_data()
            signal = generate_signal(df, strategy)
            last_price = df["close"].iloc[-1]

            # === Obținem analiza de risc
            risk = manage_risk()
            print(f"📊 RiskScore={risk['RiskScore']} | Volatilitate={risk['Volatilitate']} | DimPoz={risk['DimensiunePozitieBTC']} BTC")

            # === Verificare dacă putem tranzacționa
            if not risk["Tranzactioneaza"]:
                print("⚠️ Tranzacție refuzată: risc prea mare sau daily drawdown depășit.")
                time.sleep(15)
                continue

            # === Executăm doar dacă semnalul e clar
            if signal in ["BUY", "SELL"]:
                quantity = risk["DimensiunePozitieBTC"]
                order = execute_order(signal, last_price, quantity)
                if order:
                    save_trade(signal, last_price, quantity=quantity)
            else:
                print(f"⏳ Fără semnal clar. Ultimul preț: {last_price}")

            time.sleep(15)

        except Exception as e:
            print(f"❌ Eroare bot: {e}")
            time.sleep(10)

if __name__ == "__main__":
    run_bot()
