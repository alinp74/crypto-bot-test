import os, time, datetime
import pandas as pd
import psycopg2
from sqlalchemy import create_engine
from dotenv import load_dotenv
from kraken_client import get_price
from strategie import semnal_tranzactionare

load_dotenv()

# === Conexiune DB ===
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
conn = engine.connect()

def log_signal(symbol, signal, price):
    try:
        ts = datetime.datetime.utcnow()
        conn.execute(
            f"INSERT INTO public.signals (timestamp, symbol, signal, price) VALUES (%s,%s,%s,%s)",
            (ts, symbol, signal, price),
        )
    except Exception as e:
        print(f"❌ Eroare log_signal: {e}")

def log_trade(symbol, side, volume, price, eur_value):
    try:
        ts = datetime.datetime.utcnow()
        conn.execute(
            f"INSERT INTO public.trades (timestamp, symbol, side, volume, price, eur_value) VALUES (%s,%s,%s,%s,%s,%s)",
            (ts, symbol, side, volume, price, eur_value),
        )
    except Exception as e:
        print(f"❌ Eroare log_trade: {e}")

# === Bot loop ===
symbols = ["XXBTZEUR", "ADAEUR", "XETHZEUR"]
allocations = {"XXBTZEUR": 0.33, "ADAEUR": 0.33, "XETHZEUR": 0.34}

print("🤖 Bot pornit...")

last_analysis = time.time()

while True:
    for sym in symbols:
        signal = semnal_tranzactionare(sym)
        price = get_price(sym)
        log_signal(sym, signal, price)
        print(f"[{datetime.datetime.utcnow()}] 📈 {sym} | Semnal={signal} | Preț={price}")

    # Analiză AI o dată pe oră
    if time.time() - last_analysis > 3600:
        try:
            df = pd.read_sql("SELECT * FROM public.trades", conn)
            if len(df) > 0:
                profit = df["eur_value"].sum()
                per_symbol = df.groupby("symbol")["eur_value"].sum()
                print("=== 📊 Analiză AI ===")
                print(f"Profit total: {profit:.2f} EUR")
                print(per_symbol)
        except Exception as e:
            print(f"❌ Eroare analiză: {e}")
        last_analysis = time.time()

    time.sleep(60)
