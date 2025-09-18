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

DB_SCHEMA = os.getenv("DB_SCHEMA", "np")

try:
    engine = create_engine(db_url)
    conn = engine.connect()
    print(f"[{datetime.now()}] ✅ Connected to Postgres (schema={DB_SCHEMA})")

    # create schema and tables if not exist
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

# -------------------- STRATEGIE --------------------
def incarca_strategia():
    try:
        with open("strategy.json", "r") as f:
            strategie = json.load(f)
        print(f"[{datetime.now()}] ✅ Strategie încărcată din JSON: {strategie}")
        return strategie
    except Exception as e:
        print(f"[{datetime.now()}] ❌ Eroare încărcare strategy.json: {e}")
        # fallback minim, doar ca să nu crape
        return {
            "symbols": ["XXBTZEUR"],
            "allocations": {"XXBTZEUR": 1.0},
            "Stop_Loss": 3.0, "Take_Profit": 5.0
        }

# -------------------- BOT LOOP --------------------
def ruleaza_bot():
    strategie = incarca_strategia()
    balans_initial = get_balance()
    print(f"[{datetime.now()}] 🤖 Bot trading pornit!")
    print(f"[{datetime.now()}] 🔎 Balans inițial: {balans_initial}")

    pozitii = {simbol: {"deschis": False, "pret_intrare": 0, "cantitate": 0.0}
               for simbol in strategie.get("symbols", ["XXBTZEUR"])}

    # praguri minime EUR per tranzacție (aproximează regulile Kraken)
    MIN_ORDER_EUR = {
        "XXBTZEUR": 20,
        "XETHZEUR": 15,
        "ADAEUR": 5
    }

    next_analysis = datetime.now() + timedelta(hours=1)

    while True:
        try:
            balans = get_balance()
            eur_total = float(balans.get("ZEUR", 0))

            for simbol in strategie.get("symbols", ["XXBTZEUR"]):
                pret = get_price(simbol)
                semnal, scor, volatilitate = calculeaza_semnal(simbol, strategie)

                # salvăm date brute + semnal
                log_price_db(simbol, pret)
                log_signal_db(simbol, semnal, pret, scor, volatilitate)

                pozitie = pozitii[simbol]

                # calculăm suma alocată conform strategiei
                eur_alocat = eur_total * strategie["allocations"].get(simbol, 0.0)

                # verificăm pragul minim pentru pereche
                eur_minim = MIN_ORDER_EUR.get(simbol, 15)
                if eur_alocat < eur_minim:
                    eur_alocat = eur_minim

                # calculăm volumul (în crypto) după suma în EUR
                vol = (eur_alocat * 0.99) / pret if pret > 0 else 0

                if not pozitie["deschis"] and semnal == "BUY":
                    if float(balans.get("ZEUR", 0)) < eur_alocat * 0.99:
                        continue
                    place_market_order("buy", vol, simbol)
                    pozitie["pret_intrare"] = pret
                    pozitie["cantitate"] = vol
                    pozitie["deschis"] = True
                    log_trade_db(simbol, "BUY", vol, pret, 0.0)
                    print(f"[{datetime.now()}] ✅ ORDIN EXECUTAT: BUY {simbol} qty={vol:.6f} la {pret:.2f}")

                elif pozitie["deschis"]:
                    profit_pct = (pret - pozitie["pret_intrare"]) / pozitie["pret_intrare"] * 100

                    # SELL direct pe semnal
                    if semnal == "SELL":
                        place_market_order("sell", pozitie["cantitate"], simbol)
                        log_trade_db(simbol, "SELL_SIGNAL", pozitie["cantitate"], pret, profit_pct)
                        pozitie["deschis"] = False
                        print(f"[{datetime.now()}] ✅ ORDIN EXECUTAT: SELL_SIGNAL {simbol} qty={pozitie['cantitate']:.6f} la {pret:.2f}")

                    # SELL pe Take Profit
                    elif profit_pct >= strategie["Take_Profit"]:
                        place_market_order("sell", pozitie["cantitate"], simbol)
                        log_trade_db(simbol, "SELL_TP", pozitie["cantitate"], pret, profit_pct)
                        pozitie["deschis"] = False
                        print(f"[{datetime.now()}] ✅ ORDIN EXECUTAT: SELL_TP {simbol} qty={pozitie['cantitate']:.6f} la {pret:.2f} | Profit={profit_pct:.2f}%")

                    # SELL pe Stop Loss
                    elif profit_pct <= -strategie["Stop_Loss"]:
                        place_market_order("sell", pozitie["cantitate"], simbol)
                        log_trade_db(simbol, "SELL_SL", pozitie["cantitate"], pret, profit_pct)
                        pozitie["deschis"] = False
                        print(f"[{datetime.now()}] ✅ ORDIN EXECUTAT: SELL_SL {simbol} qty={pozitie['cantitate']:.6f} la {pret:.2f} | Profit={profit_pct:.2f}%")

                # log robust pentru semnale
                scor_safe = float(scor) if isinstance(scor, (int, float)) else 0.0
                vol_safe = float(vol) if isinstance(vol, (int, float)) else 0.0
                print(f"[{datetime.now()}] 📈 {simbol} | Semnal={semnal} | Preț={pret:.2f} | "
                      f"RiskScore={scor_safe:.2f} | Vol={vol_safe:.6f} | Balans={balans}")

            if datetime.now() >= next_analysis:
                try:
                    df = pd.read_sql(f"SELECT symbol, signal FROM {DB_SCHEMA}.signals", engine)
                    distributie = df.groupby(["symbol", "signal"]).size().unstack(fill_value=0).to_dict()
                    print(f"\n=== 📊 Analiză automată @ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===")
                    print(f"📈 Distribuție semnale: {distributie}")
                    print("===========================================\n")
                except Exception as e:
                    print(f"❌ Eroare la analiza automată: {e}")
                next_analysis = datetime.now() + timedelta(hours=1)

        except Exception as e:
            print(f"[{datetime.now()}] ❌ Eroare în rulare: {e}")

        time.sleep(10)

if __name__ == "__main__":
    ruleaza_bot()
