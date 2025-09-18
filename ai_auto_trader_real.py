import os
import time
import json
import logging
import warnings
import krakenex
import pandas as pd
from pykrakenapi import KrakenAPI
from sqlalchemy import create_engine, text
from strategie import semnal_tranzactionare

# === Configurare logging ===
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger()

# Suprimăm warninguri necritice
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)

# === Config DB ===
DB_USER = os.getenv("PGUSER")
DB_PASS = os.getenv("PGPASSWORD")
DB_HOST = os.getenv("PGHOST")
DB_PORT = os.getenv("PGPORT", "5432")
DB_NAME = os.getenv("PGDATABASE")
DB_SCHEMA = "public"

DATABASE_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(DATABASE_URL, echo=False, future=True)

# === Config Kraken ===
api = krakenex.API()
api.load_key("kraken.key")
k = KrakenAPI(api)

# === Creare tabele dacă nu există ===
def init_db():
    with engine.begin() as conn:
        conn.execute(text(f"""
        CREATE TABLE IF NOT EXISTS {DB_SCHEMA}.prices (
            id SERIAL PRIMARY KEY,
            symbol TEXT,
            price NUMERIC,
            timestamp TIMESTAMP DEFAULT NOW()
        );
        """))
        conn.execute(text(f"""
        CREATE TABLE IF NOT EXISTS {DB_SCHEMA}.signals (
            id SERIAL PRIMARY KEY,
            symbol TEXT,
            signal TEXT,
            timestamp TIMESTAMP DEFAULT NOW()
        );
        """))
        conn.execute(text(f"""
        CREATE TABLE IF NOT EXISTS {DB_SCHEMA}.trades (
            id SERIAL PRIMARY KEY,
            symbol TEXT,
            side TEXT,
            volume NUMERIC,
            price NUMERIC,
            status TEXT,
            timestamp TIMESTAMP DEFAULT NOW()
        );
        """))
    logger.info(f"✅ DB tables ready in schema {DB_SCHEMA}")

# === Funcții de DB ===
def save_price(symbol, price):
    with engine.begin() as conn:
        conn.execute(text(f"INSERT INTO {DB_SCHEMA}.prices (symbol, price) VALUES (:s, :p)"),
                     {"s": symbol, "p": price})
    logger.info(f"✅ Preț salvat în DB: {symbol}={price}")

def save_signal(symbol, signal):
    with engine.begin() as conn:
        conn.execute(text(f"INSERT INTO {DB_SCHEMA}.signals (symbol, signal) VALUES (:s, :sg)"),
                     {"s": symbol, "sg": signal})
    logger.info(f"✅ Semnal salvat în DB: {symbol}={signal}")
    # Log vizibil
    logger.info(f"📈 {symbol} | Semnal={signal}")

def save_trade(symbol, side, volume, price, status):
    with engine.begin() as conn:
        conn.execute(text(f"""
        INSERT INTO {DB_SCHEMA}.trades (symbol, side, volume, price, status)
        VALUES (:s, :side, :v, :p, :st)
        """), {"s": symbol, "side": side, "v": volume, "p": price, "st": status})
    if status == "filled":
        logger.info(f"✅ Trade EXECUTAT: {side} {volume} {symbol} la {price}")
    else:
        logger.error(f"❌ Trade EȘUAT: {status}")

# === Funcții de trading ===
def get_price(symbol):
    try:
        data = api.query_public("Ticker", {"pair": symbol})
        return float(data["result"][list(data["result"].keys())[0]]["c"][0])
    except Exception as e:
        logger.error(f"[get_price] Eroare: {e}")
        return None

def place_market_order(symbol, side, volume):
    try:
        logger.info(f"🔍 Kraken AddOrder request: side={side}, volume={volume}, pair={symbol}")
        resp = api.query_private("AddOrder", {
            "pair": symbol,
            "type": side,
            "ordertype": "market",
            "volume": str(volume)
        })
        logger.info(f"🔍 Kraken AddOrder response: {resp}")

        if resp.get("error"):
            save_trade(symbol, side, volume, None, f"Kraken error: {resp['error']}")
            return False
        else:
            save_trade(symbol, side, volume, None, "filled")
            return True
    except Exception as e:
        logger.error(f"[place_market_order] Eroare: {e}")
        save_trade(symbol, side, volume, None, f"Exception: {e}")
        return False

# === MAIN LOOP ===
if __name__ == "__main__":
    logger.info("🚀 Bot started with SQLAlchemy...")
    init_db()

    # încărcăm strategia
    try:
        with open("strategie.json", "r") as f:
            config = json.load(f)
        logger.info(f"✅ Strategie încărcată: {config}")
    except Exception as e:
        logger.error(f"❌ Strategie lipsă sau invalidă: {e}")
        exit(1)

    symbols = config.get("symbols", [])
    allocations = config.get("allocations", {})

    while True:
        for symbol in symbols:
            price = get_price(symbol)
            if not price:
                continue

            save_price(symbol, price)
            signal = semnal_tranzactionare(symbol, config)

            save_signal(symbol, signal)

            # execută ordine doar dacă nu e HOLD
            if signal in ["BUY", "SELL"]:
                volume = round(allocations.get(symbol, 0.1) * 0.001, 6)  # volum mic pentru test
                place_market_order(symbol, signal.lower(), volume)

            time.sleep(5)
