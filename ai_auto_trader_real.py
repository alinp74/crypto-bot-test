import time
import json
import os
from datetime import datetime, timedelta
import psycopg2
import pandas as pd
from kraken_client import get_price, get_balance, place_market_order
from strategie import calculeaza_semnal

print(f"[{datetime.now()}] 🚀 Bot started, initializing...")

# -------------------- CONEXIUNE DB --------------------
db_url = os.getenv("DATABASE_URL")
if db_url and db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

DB_SCHEMA = os.getenv("DB_SCHEMA", "public")  # 👈 putem seta np în Railway

try:
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()
    print(f"[{datetime.now()}] ✅ Connected to Postgres (schema={DB_SCHEMA})")
except Exception as e:
    print(f"[{datetime.now()}] ❌ Eroare la conectarea DB: {e}")
    conn = None
    cur = None

# -------------------- INIT DB --------------------
def init_db():
    if not cur:
        print(f"[{datetime.now()}] ⚠️ DB connection missing, skipping init_db")
        return
    try:
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS {DB_SCHEMA}.signals (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMP NOT NULL,
                symbol TEXT NOT NULL,
                signal TEXT NOT NULL,
                price NUMERIC,
                risk_score NUMERIC,
                volatility NUMERIC
            )
        """)
        cur.execute(f"""
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
        """)
        conn.commit()
        print(f"[{datetime.now()}] ✅ DB tables ready in schema {DB_SCHEMA}")
    except Exception as e:
        print(f"[{datetime.now()}] ❌ Eroare init_db: {e}")
        conn.rollback()

# -------------------- LOGGING DB --------------------
def log_signal_db(simbol, semnal, pret, scor, volatilitate):
    if not cur:
        return
    try:
        cur.execute(
            f"INSERT INTO {DB_SCHEMA}.signals (timestamp, symbol, signal, price, risk_score, volatility) VALUES (%s,%s,%s,%s,%s,%s)",
            (datetime.now(), simbol, semnal, pret, scor, volatilitate)
        )
        conn.commit()
    except Exception as e:
        print(f"[{datetime.now()}] ❌ Eroare log_signal_db: {e}")
        conn.rollback()

def log_trade_db(simbol, tip, cantitate, pret, profit_pct, status="EXECUTED"):
    if not cur:
        return
    try:
        cur.execute(
            f"INSERT INTO {DB_SCHEMA}.trades (timestamp, symbol, action, quantity, price, profit_pct, status) VALUES (%s,%s,%s,%s,%s,%s,%s)",
            (datetime.now(), simbol, tip, cantitate, pret, profit_pct, status)
        )
        conn.commit()
    except Exception as e:
        print(f"[{datetime.now()}] ❌ Eroare log_trade_db: {e}")
        conn.rollback()

# -------------------- STRATEGIE --------------------
def incarca_strategia():
    try:
        with open("strategy.json", "r") as f:
            strategie = json.load(f)
        print(f"[{datetime.now()}] ✅ Strategie încărcată: {strategie}")
        return strategie
    except Exception as e:
        print(f"[{datetime.now()}] ❌ Eroare la încărcarea strategiei: {e}")
        return {
            "symbols": ["XXBTZEUR"],
            "allocations": {"XXBTZEUR": 1.0},
            "RSI_Period": 7,
            "RSI_OB": 70,
            "RSI_OS": 30,
            "MACD_Fast": 12,
            "MACD_Slow": 26,
            "MACD_Signal": 9,
            "Stop_Loss": 2.0,
            "Take_Profit": 2.0,
            "Profit": 0,
            "Updated": str(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        }

# -------------------- CAPITAL --------------------
def calculeaza_capital_total(strategie, balans):
    capital_total = 0.0
    try:
        capital_total += float(balans.get("ZEUR", 0))  # EUR cash
        for simbol in strategie.get("symbols", []):
            if simbol.endswith("ZEUR"):
                asset = simbol.replace("ZEUR", "")
                if asset in balans:
                    cantitate = float(balans[asset])
                    pret = get_price(simbol)
                    capital_total += cantitate * pret
    except Exception as e:
        print(f"[{datetime.now()}] ⚠️ Eroare la calcul capital: {e}")
    return capital_total

# -------------------- ANALIZA AUTOMATĂ --------------------
def analiza_performanta():
    if not cur:
        return
    try:
        cur.execute(f"SELECT COALESCE(SUM(profit_pct), 0) FROM {DB_SCHEMA}.trades WHERE status = 'EXECUTED'")
        profit_total = cur.fetchone()[0] or 0

        cur.execute(f"SELECT COUNT(*) FROM {DB_SCHEMA}.trades WHERE action LIKE 'SELL%' AND status='EXECUTED'")
        total_sell = cur.fetchone()[0] or 0

        cur.execute(f"SELECT COUNT(*) FROM {DB_SCHEMA}.trades WHERE action LIKE 'SELL%' AND profit_pct > 0 AND status='EXECUTED'")
        sell_win = cur.fetchone()[0] or 0

        rata_succes = (sell_win / total_sell * 100) if total_sell > 0 else 0

        df = pd.read_sql(f"SELECT symbol, signal FROM {DB_SCHEMA}.signals", conn)
        distributie = df.groupby(["symbol", "signal"]).size().unstack(fill_value=0).to_dict()

        print(f"\n=== 📊 Analiza automată @ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===")
        print(f"💰 Profit total: {profit_total:.2f}%")
        print(f"✅ Rata de succes SELL: {rata_succes:.2f}% ({sell_win}/{total_sell})")
        print(f"📈 Distribuție semnale: {distributie}")
        print("===========================================\n")

    except Exception as e:
        print(f"❌ Eroare la analiza automată: {e}")

# -------------------- BOT LOOP --------------------
def ruleaza_bot():
    strategie = incarca_strategia()
    init_db()

    balans_initial = get_balance()
    capital_initial = calculeaza_capital_total(strategie, balans_initial)

    print(f"[{datetime.now()}] 🤖 Bot AI REAL pornit cu DB Postgres!")
    print(f"[{datetime.now()}] 💰 Capital inițial total detectat: {capital_initial:.2f} EUR")
    print(f"[{datetime.now()}] 🔎 Balans inițial: {balans_initial}")

    alocari_fix = {
        simbol: capital_initial * strategie.get("allocations", {}).get(simbol, 0.0)
        for simbol in strategie.get("symbols", ["XXBTZEUR"])
    }
    print(f"[{datetime.now()}] 📊 Alocări fixe (strict pe simbol): {alocari_fix}")

    pozitii = {simbol: {"deschis": False, "pret_intrare": 0, "cantitate": 0.0}
               for simbol in strategie.get("symbols", ["XXBTZEUR"])}

    next_analysis = datetime.now() + timedelta(hours=1)

    while True:
        try:
            balans = get_balance()
            for simbol in strategie.get("symbols", ["XXBTZEUR"]):
                pret = get_price(simbol)
                semnal, scor, volatilitate = calculeaza_semnal(simbol, strategie)

                log_signal_db(simbol, semnal, pret, scor, volatilitate)

                pozitie = pozitii[simbol]
                eur_alocat = alocari_fix.get(simbol, 0.0)
                vol = (eur_alocat * 0.99) / pret if pret > 0 else 0

                if not pozitie["deschis"] and semnal == "BUY":
                    if float(balans.get("ZEUR", 0)) < eur_alocat * 0.99:
                        continue
                    if eur_alocat > 10:
                        place_market_order("buy", vol, simbol)
                        pozitie["pret_intrare"] = pret
                        pozitie["cantitate"] = vol
                        pozitie["deschis"] = True
                        log_trade_db(simbol, "BUY", vol, pret, 0.0)

                elif pozitie["deschis"]:
                    profit_pct = (pret - pozitie["pret_intrare"]) / pozitie["pret_intrare"] * 100
                    if profit_pct >= strategie["Take_Profit"]:
                        place_market_order("sell", pozitie["cantitate"], simbol)
                        log_trade_db(simbol, "SELL_TP", pozitie["cantitate"], pret, profit_pct)
                        pozitie["deschis"] = False
                    elif profit_pct <= -strategie["Stop_Loss"]:
                        place_market_order("sell", pozitie["cantitate"], simbol)
                        log_trade_db(simbol, "SELL_SL", pozitie["cantitate"], pret, profit_pct)
                        pozitie["deschis"] = False

                print(f"[{datetime.now()}] 📈 {simbol} | Semnal={semnal} | Preț={pret:.2f} | RiskScore={scor:.2f} | Vol={vol:.4f} | EUR_Alocat={eur_alocat:.2f} | Balans={balans}")

            if datetime.now() >= next_analysis:
                analiza_performanta()
                next_analysis = datetime.now() + timedelta(hours=1)

        except Exception as e:
            print(f"[{datetime.now()}] ❌ Eroare în rulare: {e}")

        time.sleep(10)

if __name__ == "__main__":
    print(f"[{datetime.now()}] 🚀 Bot pornit - versiune cu DB_SCHEMA configurabil")
    init_db()
    ruleaza_bot()
