import time
import json
import csv
import os
from datetime import datetime, timedelta
import psycopg2
import pandas as pd
from kraken_client import get_price, get_balance, place_market_order
from strategie import calculeaza_semnal

# -------------------- CONEXIUNE DB --------------------
db_url = os.getenv("DATABASE_URL")

if db_url and db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

conn = psycopg2.connect(db_url)
cur = conn.cursor()
cur.execute("SET search_path TO public;")
conn.commit()

# -------------------- INIT DB --------------------
def init_db():
    cur.execute("""
        CREATE TABLE IF NOT EXISTS signals (
            id SERIAL PRIMARY KEY,
            timestamp TIMESTAMP NOT NULL,
            symbol TEXT NOT NULL,
            signal TEXT NOT NULL,
            price NUMERIC,
            risk_score NUMERIC,
            volatility NUMERIC
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS trades (
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

# -------------------- ANALIZA AUTOMATĂ --------------------
def analiza_performanta():
    try:
        # Profit total
        cur.execute("SELECT COALESCE(SUM(profit_pct), 0) FROM trades WHERE status = 'EXECUTED'")
        profit_total = cur.fetchone()[0] or 0

        # Rata de succes
        cur.execute("SELECT COUNT(*) FROM trades WHERE action LIKE 'SELL%' AND status='EXECUTED'")
        total_sell = cur.fetchone()[0] or 0

        cur.execute("SELECT COUNT(*) FROM trades WHERE action LIKE 'SELL%' AND profit_pct > 0 AND status='EXECUTED'")
        sell_win = cur.fetchone()[0] or 0

        rata_succes = (sell_win / total_sell * 100) if total_sell > 0 else 0

        # Distribuția semnalelor
        df = pd.read_sql("SELECT symbol, signal FROM signals", conn)
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
    from strategie import calculeaza_semnal
    from kraken_client import get_price, get_balance, place_market_order

    strategie = incarca_strategia()
    init_db()

    balans_initial = get_balance()
    capital_initial = calculeaza_capital_total(strategie, balans_initial)

    print(f"[{datetime.now()}] 🤖 Bot AI REAL pornit cu DB Postgres!")
    print(f"[{datetime.now()}] 💰 Capital inițial total detectat: {capital_initial:.2f} EUR")

    alocari_fix = {
        simbol: capital_initial * strategie.get("allocations", {}).get(simbol, 0.0)
        for simbol in strategie.get("symbols", ["XXBTZEUR"])
    }
    print(f"[{datetime.now()}] 📊 Alocări fixe (strict pe simbol): {alocari_fix}")

    pozitii = {simbol: {"deschis": False, "pret_intrare": 0, "cantitate": 0.0}
               for simbol in strategie.get("symbols", ["XXBTZEUR"])}

    # următoarea analiză după 1 oră
    next_analysis = datetime.now() + timedelta(hours=1)

    while True:
        try:
            balans = get_balance()

            for simbol in strategie.get("symbols", ["XXBTZEUR"]):
                pret = get_price(simbol)
                semnal, scor, volatilitate = calculeaza_semnal(simbol, strategie)

                # logăm în DB
                log_signal_db(simbol, semnal, pret, scor, volatilitate)

                pozitie = pozitii[simbol]
                eur_alocat = alocari_fix.get(simbol, 0.0)

                # Buy
                if not pozitie["deschis"] and semnal == "BUY":
                    if float(balans.get("ZEUR", 0)) < eur_alocat * 0.99:
                        continue
                    if eur_alocat > 10:
                        cantitate = (eur_alocat * 0.99) / pret
                        place_market_order("buy", cantitate, simbol)
                        pozitie["pret_intrare"] = pret
                        pozitie["cantitate"] = cantitate
                        pozitie["deschis"] = True
                        log_trade_db(simbol, "BUY", cantitate, pret, 0.0)

                # Sell
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

                print(f"[{datetime.now()}] 📈 {simbol} | Semnal={semnal} | Preț={pret:.2f} | RiskScore={scor:.2f}")

            # rulăm analiza o dată pe oră
            if datetime.now() >= next_analysis:
                analiza_performanta()
                next_analysis = datetime.now() + timedelta(hours=1)

        except Exception as e:
            print(f"[{datetime.now()}] ❌ Eroare în rulare: {e}")

        time.sleep(10)

# restul funcțiilor (incarca_strategia, calculeaza_capital_total, log_signal_db, log_trade_db) rămân neschimbate
