import os
import time
import logging
import warnings
import json
from datetime import datetime

import krakenex
from pykrakenapi import KrakenAPI
import pandas as pd
from sqlalchemy import create_engine, text

from strategie import semnal_tranzactionare
from kraken_client import get_price, place_market_order

# ----------------- CONFIG LOGGING -----------------
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger()

# ----------------- DISABLE WARNINGS -----------------
warnings.filterwarnings("ignore", category=FutureWarning)

# ----------------- DB CONNECTION -----------------
DB_URL = os.getenv("DATABASE_URL")
if DB_URL is None:
    raise ValueError("DATABASE_URL env missing")

engine = create_engine(DB_URL)

with engine.begin() as conn:
    conn.execute(text("""
    CREATE TABLE IF NOT EXISTS prices (
        id SERIAL PRIMARY KEY,
        symbol TEXT,
        price NUMERIC,
        timestamp TIMESTAMP DEFAULT NOW()
    );
    """))
    conn.execute(text("""
    CREATE TABLE IF NOT EXISTS signals (
        id SERIAL PRIMARY KEY,
        symbol TEXT,
        signal TEXT,
        timestamp TIMESTAMP DEFAULT NOW()
    );
    """))
    conn.execute(text("""
    CREATE TABLE IF NOT EXISTS trades (
        id SERIAL PRIMARY KEY,
        symbol TEXT,
        side TEXT,
        volume NUMERIC,
        price NUMERIC,
        result TEXT,
        timestamp TIMESTAMP DEFAULT NOW()
    );
    """))
logger.info("✅ DB tables ready in schema public")

# ----------------- KRAKEN INIT -----------------
api = krakenex.API()
api.load_key("kraken.key") if os.path.exists("kraken.key") else None
k = KrakenAPI(api)

# ----------------- STRATEGIE -----------------
try:
    with open("strategie.json", "r") as f:
        strategy = json.load(f)
    logger.info(f"✅ Strategie încărcată: {strategy}")
except Exception as e:
    logger.error(f"❌ Eroare încărcare strategie: {e}")
    exit(1)

# ----------------- LOOP -----------------
while True:
    for symbol in strategy["symbols"]:
        try:
            price = get_price(k, symbol)
            with engine.begin() as conn:
                conn.execute(
                    text("INSERT INTO prices(symbol, price) VALUES (:s, :p)"),
                    {"s": symbol, "p": price},
                )
            logger.info(f"✅ Preț salvat în DB: {symbol}={price}")

            # Obținem semnal
            semnal = semnal_tranzactionare(k, symbol, strategy)
            with engine.begin() as conn:
                conn.execute(
                    text("INSERT INTO signals(symbol, signal) VALUES (:s, :sig)"),
                    {"s": symbol, "sig": semnal},
                )
            logger.info(f"📈 Semnal pentru {symbol}: {semnal}")

            # Executăm doar dacă e BUY sau SELL
            if semnal in ["BUY", "SELL"]:
                volume = 0.001 if symbol == "XXBTZEUR" else 1
                result = place_market_order(api, symbol, semnal.lower(), volume)
                with engine.begin() as conn:
                    conn.execute(
                        text("INSERT INTO trades(symbol, side, volume, price, result) "
                             "VALUES (:s, :side, :v, :p, :r)"),
                        {"s": symbol, "side": semnal, "v": volume, "p": price, "r": str(result)},
                    )
                logger.info(f"✅ Ordin Kraken: {semnal} {volume} {symbol} la preț {price}")
        except Exception as e:
            logger.error(f"❌ Eroare în rulare {symbol}: {e}")

        time.sleep(5)
