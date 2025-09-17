import os
import time
import psycopg2
import pandas as pd
from sqlalchemy import create_engine
from strategie import semnal_tranzactionare
from kraken_client import get_price, get_balance, place_market_order

# ================== CONEXIUNE DB ==================
DATABASE_URL = os.getenv("DATABASE_URL")
DB_SCHEMA = "public"

engine = create_engine(DATABASE_URL)

def log_signal_db(symbol, signal, price):
    try:
        with engine.begin() as conn:
            conn.execute(
                f"""
                INSERT INTO {DB_SCHEMA}.signals (timestamp, symbol, signal, price)
                VALUES (NOW(), %s, %s, %s)
                """,
                (symbol, signal, price),
            )
    except Exception as e:
        print(f"❌ Eroare log_signal_db: {e}")

def log_trade_db(symbol, side, price, volume):
    try:
        with engine.begin() as conn:
            conn.execute(
                f"""
                INSERT INTO {DB_SCHEMA}.trades (timestamp, symbol, side, price, volume)
                VALUES (NOW(), %s, %s, %s, %s)
                """,
                (symbol, side, price, volume),
            )
    except Exception as e:
        print(f"❌ Eroare log_trade_db: {e}")

# ================== BOT LOOP ==================
SYMBOLS = ["XXBTZEUR", "ADAEUR", "XETHZEUR"]
ALLOCATIONS = {"XXBTZEUR": 0.33, "ADAEUR": 0.33, "XETHZEUR": 0.34}
COOLDOWN = 60  # secunde între cicluri

print("🤖 Bot pornit...")

while True:
    try:
        balances = get_balance()
        total_eur = balances.get("ZEUR", 0)

        for sym in SYMBOLS:
            price = get_price(sym)
            if not price:
                continue

            signal = semnal_tranzactionare(sym)
            log_signal_db(sym, signal, price)
            print(f"[{sym}] Semnal={signal} | Preț={price}")

            if signal in ["BUY", "SELL"]:
                eur_alloc = total_eur * ALLOCATIONS[sym]
                if eur_alloc <= 0:
                    continue

                if signal == "BUY":
                    volume = eur_alloc / price
                else:
                    volume = balances.get(sym.replace("EUR", ""), 0)

                txid = place_market_order(sym, signal, volume)
                if txid:
                    log_trade_db(sym, signal, price, volume)
                    print(f"✅ Executat {signal} {sym} @ {price} | Vol={volume}")

        time.sleep(COOLDOWN)

    except Exception as e:
        print(f"❌ Eroare buclă principală: {e}")
        time.sleep(10)
