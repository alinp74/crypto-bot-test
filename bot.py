import os
import time
import json
import pandas as pd
from dotenv import load_dotenv
from binance.client import Client
from binance.exceptions import BinanceAPIException
import ta  # pentru indicatori tehnici

# === CONFIG ===
load_dotenv()
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")

SYMBOL = "BTCUSDT"
TRADE_QTY = 0.001
INTERVAL = Client.KLINE_INTERVAL_1MINUTE
LIMIT = 100

# === CONECTARE BINANCE SPOT TESTNET ===
client = Client(API_KEY, API_SECRET)
client.API_URL = "https://testnet.binance.vision/api"

# === FUNCȚIE PENTRU CALCUL RSI + MACD ===
def calculate_indicators(df):
    df["rsi"] = ta.momentum.RSIIndicator(df["close"], window=14).rsi()
    macd = ta.trend.MACD(df["close"], window_slow=26, window_fast=12, window_sign=9)
    df["macd"] = macd.macd()
    df["signal"] = macd.macd_signal()
    return df

# === FUNCȚIE PENTRU ACTUALIZARE STATUS ===
def update_bot_status(status, price, rsi, macd, signal, position, pnl):
    data = {
        "status": status,
        "symbol": SYMBOL,
        "price": float(price),
        "rsi": float(rsi),
        "macd": float(macd),
        "signal": float(signal),
        "position": position,
        "profit_loss": float(pnl),
        "last_update": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    with open("bot_status.json", "w") as f:
        json.dump(data, f, indent=4)

# === BOT PRINCIPAL ===
position = None
entry_price = 0.0
profit_loss = 0.0

print("🚀 Botul a pornit! Tranzacționăm BTC/USDT pe Spot Testnet...")
while True:
    try:
        # === 1. Preluăm date recente pentru BTC/USDT ===
        klines = client.get_klines(symbol=SYMBOL, interval=INTERVAL, limit=LIMIT)
        df = pd.DataFrame(klines, columns=[
            "time", "open", "high", "low", "close", "volume", "close_time",
            "qav", "num_trades", "taker_base_vol", "taker_quote_vol", "ignore"
        ])
        df["close"] = df["close"].astype(float)

        # === 2. Calculăm indicatorii ===
        df = calculate_indicators(df)
        rsi = df["rsi"].iloc[-1]
        macd = df["macd"].iloc[-1]
        signal = df["signal"].iloc[-1]
        price = df["close"].iloc[-1]

        # === 3. Logica botului ===
        status = "⏳ Așteaptă oportunitatea..."
        if position is None:
            if rsi < 30 and macd > signal:
                order = client.order_market_buy(symbol=SYMBOL, quantity=TRADE_QTY)
                position = "LONG"
                entry_price = price
                status = f"✅ CUMPĂRAT la {price:.2f} USDT"
        elif position == "LONG":
            if rsi > 70 or macd < signal:
                order = client.order_market_sell(symbol=SYMBOL, quantity=TRADE_QTY)
                profit_loss += (price - entry_price) * TRADE_QTY
                position = None
                status = f"🔻 VÂNDUT la {price:.2f} USDT"

        # === 4. Scriem statusul în fișierul bot_status.json ===
        update_bot_status(status, price, rsi, macd, signal, position, profit_loss)

        # === 5. Afișăm informații în consolă ===
        print(f"[{pd.Timestamp.now().strftime('%H:%M:%S')}] "
              f"Preț: {price:.2f} | RSI: {rsi:.2f} | MACD: {macd:.4f} | "
              f"Poziție: {position} | Profit: {profit_loss:.2f} | Status: {status}")

        time.sleep(5)

    except BinanceAPIException as e:
        print(f"❌ Eroare Binance: {e}")
        time.sleep(10)
    except Exception as e:
        print(f"⚠️ Eroare generală: {e}")
        time.sleep(5)
