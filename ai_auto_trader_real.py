import os
import time
import json
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from kraken_client import get_price, place_market_order
from strategie import semnal_tranzactionare

# === Load .env ===
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
DB_SCHEMA = os.getenv("DB_SCHEMA", "public")

engine = create_engine(DATABASE_URL)

# === Ensure tables ===
def ensure_tables():
    with engine.begin() as conn:
        conn.execute(text(f"""
        CREATE TABLE IF NOT EXISTS {DB_SCHEMA}.prices (
            id SERIAL PRIMARY KEY,
            timestamp TIMESTAMP,
            symbol TEXT,
            price NUMERIC
        );
        """))
        conn.execute(text(f"""
        CREATE TABLE IF NOT EXISTS {DB_SCHEMA}.signals (
            id SERIAL PRIMARY KEY,
            timestamp TIMESTAMP,
            symbol TEXT,
            signal TEXT
        );
        """))
        conn.execute(text(f"""
        CREATE TABLE IF NOT EXISTS {DB_SCHEMA}.trades (
            id SERIAL PRIMARY KEY,
            timestamp TIMESTAMP,
            symbol TEXT,
            side TEXT,
            volume NUMERIC,
            price NUMERIC,
            status TEXT
        );
        """))
    print(f"[{datetime.utcnow()}] ✅ DB tables ready in schema {DB_SCHEMA}")

# === Save helpers ===
def save_price(symbol, price):
    try:
        df = pd.DataFrame([{
            "timestamp": datetime.utcnow(),
            "symbol": symbol,
            "price": price
        }])
        df.to_sql("prices", engine, schema=DB_SCHEMA, if_exists="append", index=False)
        print(f"[{datetime.utcnow()}] ✅ Preț salvat în DB: {symbol}={price}")
    except Exception as e:
        print(f"[{datetime.utcnow()}] ❌ Eroare salvare preț DB: {e}")

def save_signal(symbol, signal):
    try:
        df = pd.DataFrame([{
            "timestamp": datetime.utcnow(),
            "symbol": symbol,
            "signal": signal
        }])
        df.to_sql("signals", engine, schema=DB_SCHEMA, if_exists="append", index=False)
        print(f"[{datetime.utcnow()}] ✅ Semnal salvat în DB: {symbol}={signal}")
    except Exception as e:
        print(f"[{datetime.utcnow()}] ❌ Eroare salvare semnal DB: {e}")

def save_trade(symbol, side, volume, price, status):
    try:
        df = pd.DataFrame([{
            "timestamp": datetime.utcnow(),
            "symbol": symbol,
            "side": side,
            "volume": volume,
            "price": price,
            "status": status
        }])
        df.to_sql("trades", engine, schema=DB_SCHEMA, if_exists="append", index=False)
        print(f"[{datetime.utcnow()}] ✅ Trade salvat în DB: {symbol} {side} {volume}@{price} [{status}]")
    except Exception as e:
        print(f"[{datetime.utcnow()}] ❌ Eroare salvare trade DB: {e}")

# === Load strategy ===
def load_strategy():
    try:
        with open("strategy.json", "r") as f:
            strategy = json.load(f)
        print(f"[{datetime.utcnow()}] ✅ Strategie încărcată: {strategy}")
        return strategy
    except Exception as e:
        print(f"[{datetime.utcnow()}] ❌ Eroare încărcare strategie: {e}")
        return None

# === Bot loop ===
def run_bot():
    print(f"[{datetime.utcnow()}] 🚀 Bot started with SQLAlchemy...")
    ensure_tables()

    strategy = load_strategy()
    if not strategy:
        print("❌ Strategie lipsă. Ieșire...")
        return

    symbols = strategy["symbols"]

    while True:
        for symbol in symbols:
            try:
                # === Get price ===
                price = get_price(symbol)
                if price is None:
                    print(f"[{datetime.utcnow()}] ❌ Preț indisponibil pentru {symbol}")
                    continue

                # === Save price ===
                save_price(symbol, price)

                # === Strategy ===
                signal = semnal_tranzactionare(symbol)

                # === Save signal ===
                save_signal(symbol, signal)

                # === Execute trade if needed ===
                if signal in ["BUY", "SELL"]:
                    volume = 0.001  # simplificat
                    resp = place_market_order(symbol, signal.lower(), volume)
                    save_trade(symbol, signal, volume, price, json.dumps(resp))

                print(f"[{datetime.utcnow()}] 📈 {symbol} | Semnal={signal} | Preț={price}")

            except Exception as e:
                print(f"[{datetime.utcnow()}] ❌ Eroare în rulare: {e}")

            time.sleep(5)  # avoid Kraken rate limit

# === Entry point ===
if __name__ == "__main__":
    run_bot()
