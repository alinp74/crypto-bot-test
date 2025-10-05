import time
import json
import os
from datetime import datetime, timedelta
import pandas as pd
from sqlalchemy import create_engine, text
from kraken_client import get_price, get_balance, place_market_order
from strategie import calculeaza_semnal

print(f"[{datetime.now()}] 🚀 Bot started with SQLAlchemy...")

# -------------------- CONFIG --------------------
db_url = os.getenv("DATABASE_URL")
if db_url and db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)
DB_SCHEMA = os.getenv("DB_SCHEMA", "public")

PAIR_TO_BAL_KEY = {"XXBTZEUR": "XXBT", "XETHZEUR": "XETH"}
MIN_ORDER_EUR = {"XXBTZEUR": 20.0, "XETHZEUR": 15.0}
FEE_RATE = 0.0052   # Kraken fee total (0.26% buy + 0.26% sell)
BALANCE_EPS = 1e-12

# -------------------- DB INIT --------------------
try:
    engine = create_engine(db_url)
    conn = engine.connect()
    print(f"[{datetime.now()}] ✅ Connected to Postgres (schema={DB_SCHEMA})")

    with engine.begin() as con:
        con.execute(text(f"CREATE SCHEMA IF NOT EXISTS {DB_SCHEMA};"))
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
            CREATE TABLE IF NOT EXISTS {DB_SCHEMA}.prices (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMP NOT NULL,
                symbol TEXT NOT NULL,
                price NUMERIC
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
                profit_eur NUMERIC,
                status TEXT
            )
        """))
        con.execute(text(f"""
            CREATE TABLE IF NOT EXISTS {DB_SCHEMA}.analysis (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMP NOT NULL,
                symbol TEXT NOT NULL,
                buys INT,
                sells INT,
                avg_profit NUMERIC,
                total_profit NUMERIC,
                total_profit_eur NUMERIC
            )
        """))
    print(f"[{datetime.now()}] ✅ DB tables ready in schema {DB_SCHEMA}")

except Exception as e:
    print(f"[{datetime.now()}] ❌ DB connection error: {e}")
    conn = None


# -------------------- HELPERS --------------------
def log_signal_db(symbol, signal, price, risk, vol):
    if not conn:
        return
    try:
        with engine.begin() as con:
            con.execute(
                text(f"INSERT INTO {DB_SCHEMA}.signals (timestamp, symbol, signal, price, risk_score, volatility) "
                     "VALUES (:ts, :symbol, :signal, :price, :risk, :vol)"),
                {"ts": datetime.now(), "symbol": symbol, "signal": signal,
                 "price": float(price), "risk": float(risk), "vol": float(vol)}
            )
        print(f"[{datetime.now()}] ✅ Semnal salvat în DB: {symbol}={signal}")
    except Exception as e:
        print(f"[{datetime.now()}] ❌ Eroare log_signal_db: {e}")


def log_price_db(symbol, price):
    if not conn:
        return
    try:
        with engine.begin() as con:
            con.execute(
                text(f"INSERT INTO {DB_SCHEMA}.prices (timestamp, symbol, price) VALUES (:ts, :symbol, :price)"),
                {"ts": datetime.now(), "symbol": symbol, "price": float(price)}
            )
        print(f"[{datetime.now()}] ✅ Preț salvat în DB: {symbol}={price}")
    except Exception as e:
        print(f"[{datetime.now()}] ❌ Eroare log_price_db: {e}")


def log_trade_db(symbol, action, qty, price, profit_pct, profit_eur, status="EXECUTED"):
    if not conn:
        return
    try:
        with engine.begin() as con:
            con.execute(
                text(f"""
                    INSERT INTO {DB_SCHEMA}.trades 
                    (timestamp, symbol, action, quantity, price, profit_pct, profit_eur, status)
                    VALUES (:ts, :symbol, :action, :qty, :price, :profit_pct, :profit_eur, :status)
                """),
                {"ts": datetime.now(), "symbol": symbol, "action": action,
                 "qty": float(qty), "price": float(price),
                 "profit_pct": float(profit_pct), "profit_eur": float(profit_eur),
                 "status": status}
            )
        print(f"[{datetime.now()}] 💾 Tranzacție salvată: {symbol} {action} @ {price:.2f}")
    except Exception as e:
        print(f"[{datetime.now()}] ❌ log_trade_db error: {e}")


def log_analysis_db(df):
    if not conn or df.empty:
        return
    try:
        with engine.begin() as con:
            for row in df.itertuples():
                con.execute(
                    text(f"""
                        INSERT INTO {DB_SCHEMA}.analysis
                        (timestamp, symbol, buys, sells, avg_profit, total_profit, total_profit_eur)
                        VALUES (:ts, :symbol, :buys, :sells, :avg_profit, :total_profit, :total_profit_eur)
                    """),
                    {"ts": datetime.now(), "symbol": row.symbol,
                     "buys": int(row.buys), "sells": int(row.sells),
                     "avg_profit": float(row.avg_profit),
                     "total_profit": float(row.total_profit),
                     "total_profit_eur": float(row.total_profit_eur)}
                )
        print(f"[{datetime.now()}] ✅ Analiză salvată ({len(df)} simboluri)")
    except Exception as e:
        print(f"[{datetime.now()}] ❌ Eroare log_analysis_db: {e}")


# -------------------- STRATEGIE --------------------
def incarca_strategia():
    try:
        with open("strategy.json", "r") as f:
            strat = json.load(f)
        print(f"[{datetime.now()}] ✅ Strategie încărcată: {strat}")
        return strat
    except Exception as e:
        print(f"[{datetime.now()}] ⚠️ Strategie implicită, eroare: {e}")
        return {
            "symbols": ["XXBTZEUR", "XETHZEUR"],
            "allocations": {"XXBTZEUR": 0.5, "XETHZEUR": 0.5},
            "Stop_Loss": 2.0, "Take_Profit": 3.0, "Trailing_TP": 2.0
        }


# -------------------- POZIȚII --------------------
def sincronizeaza_pozitii(pozitii, strategie):
    balans = get_balance()
    print(f"[{datetime.now()}] 🔄 Resincronizare poziții...")
    for s in strategie.get("symbols", []):
        key = PAIR_TO_BAL_KEY.get(s, s.replace("ZEUR", ""))
        qty = float(balans.get(key, 0.0))
        if qty > 0:
            pret = get_price(s)
            pozitii[s] = {"deschis": True, "pret_intrare": pret, "cantitate": qty, "max_profit": 0.0}
            print(f"[{datetime.now()}] 🔎 {s}: OPEN qty={qty}")
        else:
            pozitii[s] = {"deschis": False, "pret_intrare": 0, "cantitate": 0, "max_profit": 0.0}


# -------------------- MAIN LOOP --------------------
def ruleaza_bot():
    strat = incarca_strategia()
    pozitii = {s: {"deschis": False, "pret_intrare": 0, "cantitate": 0, "max_profit": 0.0}
               for s in strat["symbols"]}
    sincronizeaza_pozitii(pozitii, strat)

    next_analysis = datetime.now() + timedelta(hours=1)

    while True:
        try:
            balans = get_balance()
            eur_total = float(balans.get("ZEUR", 0.0))

            for s in strat["symbols"]:
                pret = get_price(s)
                semnal, scor, vol = calculeaza_semnal(s, strat)

                # Logăm mereu prețul și semnalul
                log_price_db(s, pret)
                log_signal_db(s, semnal, pret, scor, vol)

                p = pozitii[s]
                eur_target = eur_total * strat["allocations"].get(s, 0.5)

                if not p["deschis"] and semnal == "BUY":
                    if eur_target >= MIN_ORDER_EUR.get(s, 15.0):
                        qty = (eur_target * 0.99) / pret
                        place_market_order("buy", qty, s)
                        p.update({"deschis": True, "pret_intrare": pret, "cantitate": qty, "max_profit": 0.0})
                        log_trade_db(s, "BUY", qty, pret, 0, 0)
                        print(f"[{datetime.now()}] ✅ CUMPĂRARE efectuată: {s} qty={qty:.6f} @ {pret:.2f}")

                elif p["deschis"]:
                    profit_pct = (pret - p["pret_intrare"]) / p["pret_intrare"] * 100
                    profit_eur = (pret - p["pret_intrare"]) * p["cantitate"]
                    fee = (pret * p["cantitate"]) * FEE_RATE
                    net_profit_eur = profit_eur - fee

                    if profit_pct > p["max_profit"]:
                        p["max_profit"] = profit_pct

                    # ✅ afișează profitul curent și maxim în loguri
                    print(f"[{datetime.now()}] 🧪 {s}: profit={profit_pct:.2f}% | max={p['max_profit']:.2f}% | qty={p['cantitate']:.6f}")

                    if profit_pct >= strat["Take_Profit"]:
                        place_market_order("sell", p["cantitate"], s)
                        log_trade_db(s, "SELL_TP", p["cantitate"], pret, profit_pct, net_profit_eur)
                        p.update({"deschis": False, "max_profit": 0.0})
                        print(f"[{datetime.now()}] ✅ VÂNZARE TP: {s}")

                    elif p["max_profit"] >= strat["Take_Profit"] and profit_pct <= p["max_profit"] - strat["Trailing_TP"]:
                        place_market_order("sell", p["cantitate"], s)
                        log_trade_db(s, "SELL_TRAILING", p["cantitate"], pret, profit_pct, net_profit_eur)
                        p.update({"deschis": False, "max_profit": 0.0})
                        print(f"[{datetime.now()}] ✅ VÂNZARE TRAILING: {s}")

                    elif profit_pct <= -strat["Stop_Loss"]:
                        place_market_order("sell", p["cantitate"], s)
                        log_trade_db(s, "SELL_SL", p["cantitate"], pret, profit_pct, net_profit_eur)
                        p.update({"deschis": False, "max_profit": 0.0})
                        print(f"[{datetime.now()}] ✅ VÂNZARE SL: {s}")

            # ANALIZĂ ORARĂ
            if datetime.now() >= next_analysis:
                try:
                    df = pd.read_sql(f"SELECT * FROM {DB_SCHEMA}.trades", engine)
                    if not df.empty:
                        summary = df.groupby("symbol").agg(
                            buys=("action", lambda x: (x == "BUY").sum()),
                            sells=("action", lambda x: x.str.startswith("SELL").sum()),
                            avg_profit=("profit_pct", "mean"),
                            total_profit=("profit_pct", "sum"),
                            total_profit_eur=("profit_eur", "sum")
                        ).reset_index()
                        print(f"\n=== 💰 Summary @ {datetime.now()} ===\n{summary}\n")
                        log_analysis_db(summary)
                except Exception as e:
                    print(f"❌ Eroare analiză: {e}")
                next_analysis = datetime.now() + timedelta(hours=1)

        except Exception as e:
            print(f"[{datetime.now()}] ❌ Loop error: {e}")

        time.sleep(10)


if __name__ == "__main__":
    ruleaza_bot()
