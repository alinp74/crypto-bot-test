import time
import json
import os
from datetime import datetime, timedelta
import pandas as pd
from sqlalchemy import create_engine, text
from kraken_client import get_price, get_balance, place_market_order
from strategie import calculeaza_semnal

print(f"[{datetime.now()}] 🚀 Bot started with SQLAlchemy...")

# -------------------- DB INIT --------------------
db_url = os.getenv("DATABASE_URL")
if db_url and db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

DB_SCHEMA = os.getenv("DB_SCHEMA", "public")

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
            CREATE TABLE IF NOT EXISTS {DB_SCHEMA}.prices (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMP NOT NULL,
                symbol TEXT NOT NULL,
                price NUMERIC
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
                total_profit NUMERIC
            )
        """))
    print(f"[{datetime.now()}] ✅ DB tables ready in schema {DB_SCHEMA}")

except Exception as e:
    print(f"[{datetime.now()}] ❌ DB connection error: {e}")
    conn = None

# -------------------- DB LOGGING --------------------
def log_signal_db(simbol, semnal, pret, scor, volatilitate):
    if not conn:
        return
    try:
        with engine.begin() as con:
            con.execute(
                text(f"INSERT INTO {DB_SCHEMA}.signals (timestamp, symbol, signal, price, risk_score, volatility) "
                     "VALUES (:ts, :symbol, :signal, :price, :risk, :vol)"),
                {
                    "ts": datetime.now(),
                    "symbol": str(simbol),
                    "signal": str(semnal),
                    "price": float(pret) if pret is not None else None,
                    "risk": float(scor) if scor is not None else None,
                    "vol": float(volatilitate) if volatilitate is not None else None
                }
            )
        print(f"[{datetime.now()}] ✅ Semnal salvat în DB: {simbol}={semnal}")
    except Exception as e:
        print(f"[{datetime.now()}] ❌ Eroare log_signal_db: {e}")

def log_trade_db(simbol, tip, cantitate, pret, profit_pct, status="EXECUTED"):
    if not conn:
        return
    try:
        with engine.begin() as con:
            con.execute(
                text(f"INSERT INTO {DB_SCHEMA}.trades (timestamp, symbol, action, quantity, price, profit_pct, status) "
                     "VALUES (:ts, :symbol, :action, :qty, :price, :profit, :status)"),
                {
                    "ts": datetime.now(),
                    "symbol": str(simbol),
                    "action": str(tip),
                    "qty": float(cantitate) if cantitate is not None else None,
                    "price": float(pret) if pret is not None else None,
                    "profit": float(profit_pct) if profit_pct is not None else None,
                    "status": str(status)
                }
            )
        print(f"[{datetime.now()}] 💾 Tranzacție salvată în DB: {simbol} {tip} @ {pret:.2f} (qty={cantitate:.6f})")
    except Exception as e:
        print(f"[{datetime.now()}] ❌ Eroare log_trade_db: {e}")

def log_price_db(simbol, pret):
    if not conn:
        return
    try:
        with engine.begin() as con:
            con.execute(
                text(f"INSERT INTO {DB_SCHEMA}.prices (timestamp, symbol, price) VALUES (:ts, :symbol, :price)"),
                {
                    "ts": datetime.now(),
                    "symbol": str(simbol),
                    "price": float(pret) if pret is not None else None
                }
            )
        print(f"[{datetime.now()}] ✅ Preț salvat în DB: {simbol}={pret}")
    except Exception as e:
        print(f"[{datetime.now()}] ❌ Eroare log_price_db: {e}")

def log_analysis_db(df):
    if not conn or df.empty:
        return
    try:
        with engine.begin() as con:
            for row in df.itertuples():
                con.execute(
                    text(f"""INSERT INTO {DB_SCHEMA}.analysis
                        (timestamp, symbol, buys, sells, avg_profit, total_profit)
                        VALUES (:ts, :symbol, :buys, :sells, :avg_profit, :total_profit)"""),
                    {
                        "ts": datetime.now(),
                        "symbol": row.symbol,
                        "buys": int(row.buys),
                        "sells": int(row.sells),
                        "avg_profit": float(row.avg_profit) if row.avg_profit is not None else 0.0,
                        "total_profit": float(row.total_profit) if row.total_profit is not None else 0.0
                    }
                )
        print(f"[{datetime.now()}] ✅ Analiza salvată în DB pentru {len(df)} monede")
    except Exception as e:
        print(f"[{datetime.now()}] ❌ Eroare log_analysis_db: {e}")

# -------------------- STRATEGIE --------------------
def incarca_strategia():
    try:
        with open("strategy.json", "r") as f:
            strategie = json.load(f)
        print(f"[{datetime.now()}] ✅ Strategie încărcată din JSON: {strategie}")
        return strategie
    except Exception as e:
        print(f"[{datetime.now()}] ❌ Eroare încărcare strategy.json: {e}")
        return {
            "symbols": ["XXBTZEUR"],
            "allocations": {"XXBTZEUR": 1.0},
            "Stop_Loss": 2.0, "Take_Profit": 4.0, "Trailing_TP": 1.5
        }

# -------------------- SYNC POZITII --------------------
def sincronizeaza_pozitii(pozitii, strategie):
    balans = get_balance()
    for simbol in strategie.get("symbols", []):
        coin = simbol.replace("EUR", "").replace("XXBT", "XXBT").replace("XETH", "XETH")
        if coin in balans and float(balans[coin]) > 0:
            pozitii[simbol]["deschis"] = True
            pozitii[simbol]["cantitate"] = float(balans[coin])
            try:
                df = pd.read_sql(
                    f"SELECT action, price, timestamp FROM {DB_SCHEMA}.trades "
                    f"WHERE symbol='{simbol}' ORDER BY timestamp DESC LIMIT 2",
                    engine
                )
                if not df.empty:
                    last_action = df.iloc[0]["action"]
                    if last_action.startswith("SELL"):
                        pozitii[simbol]["deschis"] = False
                        pozitii[simbol]["pret_intrare"] = 0
                        print(f"[{datetime.now()}] 🔎 {simbol}: ultima tranzacție a fost SELL → poziția e închisă.")
                    else:
                        pozitii[simbol]["pret_intrare"] = float(df.iloc[0]["price"])
                        print(f"[{datetime.now()}] 🔎 {simbol}: poziție deschisă la {pozitii[simbol]['pret_intrare']}")
                else:
                    pozitii[simbol]["pret_intrare"] = get_price(simbol)
                    print(f"[{datetime.now()}] ⚠️ {simbol}: nu am găsit tranzacții, fallback la preț curent.")
            except Exception as e:
                pozitii[simbol]["pret_intrare"] = get_price(simbol)
                print(f"[{datetime.now()}] ⚠️ {simbol}: eroare la citirea tranzacțiilor, fallback la preț curent. {e}")
            pozitii[simbol]["max_profit"] = 0.0

# -------------------- BOT LOOP --------------------
def ruleaza_bot():
    strategie = incarca_strategia()
    balans_initial = get_balance()
    print(f"[{datetime.now()}] 🤖 Bot trading pornit!")
    print(f"[{datetime.now()}] 🔎 Balans inițial: {balans_initial}")

    pozitii = {simbol: {"deschis": False, "pret_intrare": 0, "cantitate": 0.0, "max_profit": 0.0}
               for simbol in strategie.get("symbols", ["XXBTZEUR"])}

    sincronizeaza_pozitii(pozitii, strategie)

    MIN_ORDER_EUR = {"XXBTZEUR": 20, "XETHZEUR": 15, "ADAEUR": 5}
    next_analysis = datetime.now() + timedelta(hours=1)

    while True:
        try:
            balans = get_balance()
            eur_total = float(balans.get("ZEUR", 0))

            for simbol in strategie.get("symbols", ["XXBTZEUR"]):
                pret = get_price(simbol)
                semnal, scor, volatilitate = calculeaza_semnal(simbol, strategie)

                log_price_db(simbol, pret)
                log_signal_db(simbol, semnal, pret, scor, volatilitate)

                pozitie = pozitii[simbol]

                eur_alocat = eur_total * strategie["allocations"].get(simbol, 0.0)
                eur_minim = MIN_ORDER_EUR.get(simbol, 15)
                if eur_alocat < eur_minim:
                    eur_alocat = eur_minim
                vol = (eur_alocat * 0.99) / pret if pret > 0 else 0

                if not pozitie["deschis"] and semnal == "BUY":
                    if float(balans.get("ZEUR", 0)) < eur_alocat * 0.99:
                        continue
                    place_market_order("buy", vol, simbol)
                    pozitie["pret_intrare"] = pret
                    pozitie["cantitate"] = vol
                    pozitie["deschis"] = True
                    pozitie["max_profit"] = 0.0
                    log_trade_db(simbol, "BUY", vol, pret, 0.0)
                    print(f"[{datetime.now()}] ✅ ORDIN EXECUTAT: BUY {simbol} qty={vol:.6f} la {pret:.2f}")

                elif pozitie["deschis"]:
                    if pozitie["pret_intrare"] <= 0:
                        print(f"[{datetime.now()}] ⚠️ {simbol}: pret_intrare invalid, SL/TP nu se aplică.")
                        continue

                    profit_pct = (pret - pozitie["pret_intrare"]) / pozitie["pret_intrare"] * 100
                    if profit_pct > pozitie.get("max_profit", 0):
                        pozitii[simbol]["max_profit"] = profit_pct

                    # DEBUG log
                    print(f"[{datetime.now()}] DEBUG {simbol}: pret_intrare={pozitie['pret_intrare']}, "
                          f"pret_curent={pret}, profit_pct={profit_pct:.2f}%")

                    if profit_pct >= strategie["Take_Profit"]:
                        place_market_order("sell", pozitie["cantitate"], simbol)
                        log_trade_db(simbol, "SELL_TP", pozitie["cantitate"], pret, profit_pct)
                        pozitie.update({"deschis": False, "max_profit": 0.0})
                        print(f"[{datetime.now()}] ✅ ORDIN EXECUTAT: SELL_TP {simbol} | Profit={profit_pct:.2f}%")

                    elif pozitie["max_profit"] >= strategie["Take_Profit"]:
                        trailing = strategie.get("Trailing_TP", 1.5)
                        if profit_pct <= pozitie["max_profit"] - trailing:
                            place_market_order("sell", pozitie["cantitate"], simbol)
                            log_trade_db(simbol, "SELL_TRAILING", pozitie["cantitate"], pret, profit_pct)
                            pozitie.update({"deschis": False, "max_profit": 0.0})
                            print(f"[{datetime.now()}] ✅ ORDIN EXECUTAT: SELL_TRAILING {simbol} | Profit={profit_pct:.2f}%")

                    elif profit_pct <= -strategie["Stop_Loss"]:
                        place_market_order("sell", pozitie["cantitate"], simbol)
                        log_trade_db(simbol, "SELL_SL", pozitie["cantitate"], pret, profit_pct)
                        pozitie.update({"deschis": False, "max_profit": 0.0})
                        print(f"[{datetime.now()}] ✅ ORDIN EXECUTAT: SELL_SL {simbol} | Profit={profit_pct:.2f}%")

            if datetime.now() >= next_analysis:
                try:
                    df_trades = pd.read_sql(f"SELECT * FROM {DB_SCHEMA}.trades", engine)
                    if not df_trades.empty:
                        summary = df_trades.groupby("symbol").agg(
                            buys=("action", lambda x: (x == "BUY").sum()),
                            sells=("action", lambda x: x.str.startswith("SELL").sum()),
                            avg_profit=("profit_pct", "mean"),
                            total_profit=("profit_pct", "sum")
                        ).reset_index()

                        print(f"\n=== 💰 Analiză profit/pierdere @ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===")
                        print(summary)
                        log_analysis_db(summary)

                    print("===========================================\n")
                except Exception as e:
                    print(f"❌ Eroare la analiza automată: {e}")

                next_analysis = datetime.now() + timedelta(hours=1)

        except Exception as e:
            print(f"[{datetime.now()}] ❌ Eroare în rulare: {e}")

        time.sleep(10)

if __name__ == "__main__":
    ruleaza_bot()
