import os
import json
import time
import logging
import datetime
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
import kraken_client
from strategie import semnal_tranzactionare

# ---------------- CONFIG ---------------- #
load_dotenv()
DB_URL = os.getenv("DATABASE_URL")
DB_SCHEMA = "public"

# Conexiune SQLAlchemy
engine = create_engine(DB_URL)

# Config logging
logging.basicConfig(level=logging.INFO, format="%(message)s")

# Limite minime Kraken (aprox în EUR)
MIN_ORDER_EUR = {
    "XXBTZEUR": 20.0,   # BTC ~20€
    "XETHZEUR": 10.0,   # ETH ~10€
    "ADAEUR": 5.0       # ADA ~5€
}

# ---------------- FUNCȚII DB ---------------- #
def log_price(symbol, price):
    try:
        with engine.begin() as conn:
            conn.execute(
                text(f"INSERT INTO {DB_SCHEMA}.prices (timestamp, symbol, price) VALUES (:t,:s,:p)"),
                {"t": datetime.datetime.utcnow(), "s": symbol, "p": float(price)}
            )
        logging.info(f"[{datetime.datetime.utcnow()}] ✅ Preț salvat în DB: {symbol}={price}")
    except Exception as e:
        logging.error(f"❌ Eroare log_price: {e}")

def log_signal(symbol, signal, reason=""):
    try:
        with engine.begin() as conn:
            conn.execute(
                text(f"INSERT INTO {DB_SCHEMA}.signals (timestamp, symbol, signal, reason) VALUES (:t,:s,:sig,:r)"),
                {"t": datetime.datetime.utcnow(), "s": symbol, "sig": signal, "r": reason}
            )
        logging.info(f"[{datetime.datetime.utcnow()}] ✅ Semnal salvat în DB: {symbol}={signal}")
    except Exception as e:
        logging.error(f"❌ Eroare log_signal: {e}")

def log_trade(symbol, side, volume, price, status):
    try:
        with engine.begin() as conn:
            conn.execute(
                text(f"""INSERT INTO {DB_SCHEMA}.trades 
                        (timestamp, symbol, side, volume, price, status) 
                        VALUES (:t,:s,:side,:v,:p,:st)"""),
                {"t": datetime.datetime.utcnow(), "s": symbol, "side": side,
                 "v": float(volume), "p": float(price) if price else None, "st": status}
            )
        logging.info(f"[{datetime.datetime.utcnow()}] ✅ Trade salvat în DB: {side} {symbol} vol={volume} st={status}")
    except Exception as e:
        logging.error(f"❌ Eroare log_trade: {e}")

# ---------------- MAIN BOT ---------------- #
if __name__ == "__main__":
    logging.info(f"[{datetime.datetime.utcnow()}] 🚀 Bot started with SQLAlchemy...")

    try:
        with engine.begin() as conn:
            conn.execute(text("SELECT 1"))
        logging.info(f"[{datetime.datetime.utcnow()}] ✅ Connected to Postgres (schema={DB_SCHEMA})")
    except Exception as e:
        logging.error(f"❌ Eroare conectare DB: {e}")
        exit(1)

    # Load strategie
    with open("strategie.json", "r") as f:
        strategy = json.load(f)
    logging.info(f"[{datetime.datetime.utcnow()}] ✅ Strategie încărcată: {strategy}")

    symbols = strategy["symbols"]
    allocations = strategy["allocations"]

    logging.info(f"[{datetime.datetime.utcnow()}] 🤖 Bot AI REAL pornit cu SQLAlchemy!")

    while True:
        for symbol in symbols:
            try:
                price = kraken_client.get_price(symbol)
                log_price(symbol, price)

                signal = semnal_tranzactionare(symbol)
                log_signal(symbol, signal)

                # ---------------- ORDER EXECUTION ---------------- #
                if signal in ["BUY", "SELL"]:
                    balans = kraken_client.get_balance()
                    eur_balance = balans.get("ZEUR", 0.0)

                    eur_alloc = eur_balance * allocations[symbol]
                    min_eur = MIN_ORDER_EUR.get(symbol, 5.0)

                    if eur_alloc < min_eur:
                        msg = f"IGNORED_TOO_SMALL (alloc={eur_alloc:.2f} < min={min_eur})"
                        logging.info(f"[{datetime.datetime.utcnow()}] ⚠️ {symbol} {signal} ignorat: {msg}")
                        log_trade(symbol, signal, 0, price, msg)
                        continue

                    # Calculează volumul
                    volume = eur_alloc / price

                    logging.info(f"[{datetime.datetime.utcnow()}] 🔍 Kraken AddOrder request: side={signal.lower()}, volume={volume}, pair={symbol}")
                    resp = kraken_client.place_market_order(symbol, signal.lower(), volume)
                    logging.info(f"[{datetime.datetime.utcnow()}] 🔍 Kraken AddOrder response: {resp}")

                    if resp.get("error"):
                        log_trade(symbol, signal, volume, price, f"ERROR: {resp['error']}")
                    else:
                        log_trade(symbol, signal, volume, price, "FILLED")

            except Exception as e:
                logging.error(f"[{datetime.datetime.utcnow()}] ❌ Eroare în rulare: {e}")

        time.sleep(60)  # 1 minut între cicluri
