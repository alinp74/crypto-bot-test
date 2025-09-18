import os
import time
import logging
from datetime import datetime
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

from kraken_client import get_price, get_ohlc, place_market_order
from strategie import semnal_tranzactionare

# =======================
# Config Logging
# =======================
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger()

# =======================
# Încarcă variabile din .env
# =======================
load_dotenv()

DB_URL = os.getenv("DATABASE_URL")
if DB_URL is None:
    raise ValueError("❌ DATABASE_URL lipsește din .env")

engine = create_engine(DB_URL)

# =======================
# Creare tabele (dacă lipsesc)
# =======================
with engine.begin() as conn:
    conn.execute(text("""
    CREATE TABLE IF NOT EXISTS prices (
        id SERIAL PRIMARY KEY,
        timestamp TIMESTAMP NOT NULL,
        symbol TEXT NOT NULL,
        price NUMERIC NOT NULL
    )
    """))
    conn.execute(text("""
    CREATE TABLE IF NOT EXISTS signals (
        id SERIAL PRIMARY KEY,
        timestamp TIMESTAMP NOT NULL,
        symbol TEXT NOT NULL,
        signal TEXT NOT NULL
    )
    """))
    conn.execute(text("""
    CREATE TABLE IF NOT EXISTS trades (
        id SERIAL PRIMARY KEY,
        timestamp TIMESTAMP NOT NULL,
        symbol TEXT NOT NULL,
        side TEXT NOT NULL,
        volume NUMERIC NOT NULL,
        price NUMERIC,
        status TEXT
    )
    """))

logger.info(f"[{datetime.now()}] ✅ DB tables ready in schema public")

# =======================
# Încarcă strategia
# =======================
strategie = {
    "symbols": ["XXBTZEUR", "ADAEUR", "XETHZEUR"],
    "allocations": {"XXBTZEUR": 0.33, "ADAEUR": 0.33, "XETHZEUR": 0.34},
    "RSI_Period": 7,
    "RSI_OB": 70,
    "RSI_OS": 30,
    "MACD_Fast": 12,
    "MACD_Slow": 26,
    "MACD_Signal": 9,
    "Stop_Loss": 3.0,
    "Take_Profit": 2.0,
    "Profit": 0,
    "Updated": str(datetime.now())
}

logger.info(f"[{datetime.now()}] ✅ Strategie încărcată: {strategie}")

# =======================
# Loop principal
# =======================
while True:
    try:
        for symbol in strategie["symbols"]:
            # 1. Obține preț curent
            price = get_price(symbol)
            ts = datetime.now()

            # Salvează în DB
            with engine.begin() as conn:
                conn.execute(
                    text("INSERT INTO prices (timestamp, symbol, price) VALUES (:ts, :sym, :pr)"),
                    {"ts": ts, "sym": symbol, "pr": price}
                )
            logger.info(f"[{ts}] ✅ Preț salvat în DB: {symbol}={price}")

            # 2. Obține OHLC și semnal
            df = get_ohlc(symbol)
            signal = semnal_tranzactionare(df, symbol, strategie)  # <-- FIX

            # Salvează semnal
            with engine.begin() as conn:
                conn.execute(
                    text("INSERT INTO signals (timestamp, symbol, signal) VALUES (:ts, :sym, :sig)"),
                    {"ts": ts, "sym": symbol, "sig": signal}
                )
            logger.info(f"[{ts}] ✅ Semnal salvat în DB: {symbol}={signal}")

            # 3. Execută ordin dacă e BUY/SELL
            if signal in ["BUY", "SELL"]:
                volume = 10 / price  # Exemplu: ~10 EUR alocați
                response = place_market_order(symbol, signal.lower(), volume)

                with engine.begin() as conn:
                    conn.execute(
                        text("""INSERT INTO trades (timestamp, symbol, side, volume, price, status)
                                VALUES (:ts, :sym, :side, :vol, :pr, :st)"""),
                        {
                            "ts": ts,
                            "sym": symbol,
                            "side": signal,
                            "vol": volume,
                            "pr": price,
                            "st": str(response),
                        }
                    )
                logger.info(f"[{ts}] 🛒 Tranzacție {signal} {symbol} la {price}, vol={volume}")

        time.sleep(10)

    except Exception as e:
        logger.error(f"[{datetime.now()}] ❌ Eroare în rulare: {e}")
        time.sleep(5)
