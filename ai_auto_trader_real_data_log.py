import time
import os
import json
from datetime import datetime
from sqlalchemy import create_engine, text
from kraken_client import get_price
from strategie import calculeaza_semnal

print(f"[{datetime.now()}] 📝 Data Logger starting...")

# DB INIT
db_url = os.getenv("DATABASE_URL")
if db_url and db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)
DB_SCHEMA = os.getenv("DB_SCHEMA", "public")

engine = create_engine(db_url)
conn = engine.connect()
with engine.begin() as con:
    con.execute(text(f"CREATE SCHEMA IF NOT EXISTS {DB_SCHEMA};"))
    con.execute(text(f"""
        CREATE TABLE IF NOT EXISTS {DB_SCHEMA}.signals(
            id SERIAL PRIMARY KEY,
            timestamp TIMESTAMP NOT NULL,
            symbol TEXT NOT NULL,
            signal TEXT NOT NULL,
            price NUMERIC,
            risk_score NUMERIC,
            volatility NUMERIC
        )
    """))
    con.execute(text(f"""
        CREATE TABLE IF NOT EXISTS {DB_SCHEMA}.prices(
            id SERIAL PRIMARY KEY,
            timestamp TIMESTAMP NOT NULL,
            symbol TEXT NOT NULL,
            price NUMERIC
        )
    """))
print(f"[{datetime.now()}] ✅ Logger DB ready in schema {DB_SCHEMA}")

def incarca_strategia():
    try:
        with open("strategy.json","r") as f:
            return json.load(f)
    except:
        return {"symbols": ["XXBTZEUR","XETHZEUR"], "RSI_Period": 10, "RSI_OB": 70, "RSI_OS": 30}

def log_price(symbol, price):
    try:
        with engine.begin() as con:
            con.execute(
                text(f"INSERT INTO {DB_SCHEMA}.prices (timestamp, symbol, price) VALUES (:ts,:s,:p)"),
                {"ts": datetime.now(), "s": symbol, "p": float(price)}
            )
        print(f"[{datetime.now()}] 📦 price -> {symbol} = {price}")
    except Exception as e:
        print(f"[{datetime.now()}] ❌ price log error: {e}")

def log_signal(symbol, signal, price, score, vol):
    try:
        with engine.begin() as con:
            con.execute(
                text(f"INSERT INTO {DB_SCHEMA}.signals (timestamp, symbol, signal, price, risk_score, volatility) "
                     "VALUES (:ts,:s,:sig,:p,:r,:v)"),
                {"ts": datetime.now(), "s": symbol, "sig": str(signal),
                 "p": float(price) if price is not None else None,
                 "r": float(score) if score is not None else None,
                 "v": float(vol) if vol is not None else None}
            )
        print(f"[{datetime.now()}] 📨 signal -> {symbol} = {signal}")
    except Exception as e:
        print(f"[{datetime.now()}] ❌ signal log error: {e}")

def run_logger():
    strat = incarca_strategia()
    symbols = strat.get("symbols", ["XXBTZEUR","XETHZEUR"])
    while True:
        try:
            for s in symbols:
                price = get_price(s)
                signal, score, vol = calculeaza_semnal(s, strat)
                log_price(s, price)
                log_signal(s, signal, price, score, vol)
            # interval logging (nu foarte agresiv ca să respecte rate limit)
            time.sleep(10)
        except Exception as e:
            print(f"[{datetime.now()}] ❌ logger loop error: {e}")
            time.sleep(10)

if __name__ == "__main__":
    run_logger()
