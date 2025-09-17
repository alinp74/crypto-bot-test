import os
import time
import json
from datetime import datetime, timedelta
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
import kraken_client
from strategie import semnal_tranzactionare

# ============================================================
# Configurare
# ============================================================
load_dotenv()

db_url = os.getenv("DATABASE_URL")
if db_url and db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

DB_SCHEMA = os.getenv("DB_SCHEMA", "public")

engine = create_engine(db_url)

# Creăm tabelele dacă nu există
with engine.begin() as con:
    con.execute(text(f"""
        CREATE TABLE IF NOT EXISTS {DB_SCHEMA}.prices (
            id SERIAL PRIMARY KEY,
            timestamp TIMESTAMP NOT NULL,
            symbol TEXT NOT NULL,
            price NUMERIC
        )
    """))
    con.execute(text(f"""
        CREATE TABLE IF NOT EXISTS {DB_SCHEMA}.signals (
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
        CREATE TABLE IF NOT EXISTS {DB_SCHEMA}.trades (
            id SERIAL PRIMARY KEY,
            timestamp TIMESTAMP NOT NULL,
            symbol TEXT NOT NULL,
            action TEXT NOT NULL,
            quantity NUMERIC,
            price NUMERIC,
            profit_pct NUMERIC,
            status TEXT
        )
    """))
    con.execute(text(f"""
        CREATE TABLE IF NOT EXISTS {DB_SCHEMA}.analysis (
            id SERIAL PRIMARY KEY,
            timestamp TIMESTAMP NOT NULL,
            metric TEXT NOT NULL,
            value TEXT
        )
    """))

print(f"[{datetime.now()}] ✅ Connected to Postgres (schema={DB_SCHEMA})")

# ============================================================
# Funcții log
# ============================================================
def log_price_db(symbol, price):
    with engine.begin() as con:
        con.execute(
            text(f"INSERT INTO {DB_SCHEMA}.prices (timestamp, symbol, price) VALUES (:ts, :symbol, :price)"),
            {"ts": datetime.now(), "symbol": symbol, "price": price}
        )

def log_signal_db(symbol, signal, price, risk_score, volatility):
    with engine.begin() as con:
        con.execute(
            text(f"""INSERT INTO {DB_SCHEMA}.signals 
                     (timestamp, symbol, signal, price, risk_score, volatility)
                     VALUES (:ts, :symbol, :signal, :price, :rs, :vol)"""),
            {"ts": datetime.now(), "symbol": symbol, "signal": signal,
             "price": price, "rs": risk_score, "vol": volatility}
        )

def log_trade_db(symbol, action, qty, price, profit_pct, status):
    with engine.begin() as con:
        con.execute(
            text(f"""INSERT INTO {DB_SCHEMA}.trades 
                     (timestamp, symbol, action, quantity, price, profit_pct, status)
                     VALUES (:ts, :symbol, :action, :qty, :price, :profit, :status)"""),
            {"ts": datetime.now(), "symbol": symbol, "action": action,
             "qty": qty, "price": price, "profit": profit_pct, "status": status}
        )

def log_analysis_db(metric, value):
    with engine.begin() as con:
        con.execute(
            text(f"INSERT INTO {DB_SCHEMA}.analysis (timestamp, metric, value) VALUES (:ts, :metric, :value)"),
            {"ts": datetime.now(), "metric": metric, "value": str(value)}
        )

# ============================================================
# Config strategii
# ============================================================
with open("strategy.json", "r") as f:
    strategie = json.load(f)

symbols = strategie["symbols"]
allocations = strategie["allocations"]

print(f"[{datetime.now()}] 🤖 Bot AI REAL pornit cu perechi: {symbols}")
print(f"[{datetime.now()}] 📊 Alocări: {allocations}")

next_analysis = datetime.now() + timedelta(hours=1)

# ============================================================
# Loop principal
# ============================================================
while True:
    for symbol in symbols:
        try:
            # Obține preț
            pret = kraken_client.get_price(symbol)
            log_price_db(symbol, pret)

            # Generează semnal
            semnal, scor_risc, volatilitate = semnal_tranzactionare(symbol)
            log_signal_db(symbol, semnal, pret, scor_risc, volatilitate)

            print(f"[{datetime.now()}] 📈 {symbol} | Semnal={semnal} | Preț={pret:.2f} | Risk={scor_risc:.2f}")

            # Execută ordine
            if semnal == "BUY":
                eur_alocat = allocations.get(symbol, 0) * kraken_client.get_total_capital()
                qty = kraken_client.calc_order_size(symbol, pret, capital_total=eur_alocat)
                if qty > 0:
                    resp = kraken_client.place_market_order(symbol, "buy", qty)
                    status = "executed" if resp and not resp.get("error") else "failed"
                    log_trade_db(symbol, "BUY", qty, pret, 0, status)

            elif semnal == "SELL":
                qty = kraken_client.get_balance_qty(symbol)
                if qty > 0:
                    resp = kraken_client.place_market_order(symbol, "sell", qty)
                    status = "executed" if resp and not resp.get("error") else "failed"
                    log_trade_db(symbol, "SELL", qty, pret, 0, status)

        except Exception as e:
            print(f"[{datetime.now()}] ❌ Eroare {symbol}: {e}")

    # ========================================================
    # Analiză automată o dată pe oră
    # ========================================================
    if datetime.now() >= next_analysis:
        try:
            df_signals = pd.read_sql(f"SELECT symbol, signal FROM {DB_SCHEMA}.signals", engine)
            distributie = df_signals.groupby(["symbol", "signal"]).size().unstack(fill_value=0).to_dict()

            df_trades = pd.read_sql(f"SELECT * FROM {DB_SCHEMA}.trades", engine)
            nr_tranzactii = len(df_trades)

            if nr_tranzactii > 0:
                profit_total = df_trades["profit_pct"].fillna(0).sum()
                profit_mediu = df_trades["profit_pct"].fillna(0).mean()
            else:
                profit_total = 0
                profit_mediu = 0

            # Logs globale
            print(f"\n=== 📊 Analiză automată @ {datetime.now()} ===")
            print(f"📈 Distribuție semnale: {distributie}")
            print(f"💰 Tranzacții: {nr_tranzactii}")
            print(f"📊 Profit total: {profit_total:.2f}%")
            print(f"📊 Profit mediu: {profit_mediu:.2f}%")

            # Analiză pe monedă
            if nr_tranzactii > 0:
                per_symbol = df_trades.groupby("symbol")["profit_pct"].agg(["count", "sum", "mean"]).reset_index()
                for _, row in per_symbol.iterrows():
                    simbol = row["symbol"]
                    print(f"🔹 {simbol}: tranzacții={int(row['count'])}, total={row['sum']:.2f}%, mediu={row['mean']:.2f}%")
                    log_analysis_db(f"{simbol}_trades_count", int(row["count"]))
                    log_analysis_db(f"{simbol}_profit_total_pct", float(row["sum"]))
                    log_analysis_db(f"{simbol}_profit_avg_pct", float(row["mean"]))

            # Salvăm global
            log_analysis_db("signal_distribution", distributie)
            log_analysis_db("profit_total_pct", profit_total)
            log_analysis_db("profit_avg_pct", profit_mediu)
            log_analysis_db("trades_count", nr_tranzactii)

        except Exception as e:
            print(f"❌ Eroare analiză automată: {e}")

        next_analysis = datetime.now() + timedelta(hours=1)

    time.sleep(60)
