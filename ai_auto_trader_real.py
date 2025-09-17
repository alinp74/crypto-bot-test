import time
import json
import csv
import os
from datetime import datetime
import psycopg2
from kraken_client import get_price, get_balance, place_market_order
from strategie import calculeaza_semnal


# -------------------- CONEXIUNE DB --------------------
conn = psycopg2.connect(os.getenv("DATABASE_URL"))
cur = conn.cursor()

def init_db():
    """Creează tabelele signals și trades dacă nu există"""
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


# -------------------- LOGGING CSV --------------------
TRADE_FILE = "trades_log.csv"
SIGNAL_FILE = "signals_log.csv"

def init_trade_log():
    if not os.path.exists(TRADE_FILE):
        with open(TRADE_FILE, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Timp", "Simbol", "Tip", "Cantitate", "Preț", "Profit %"])

def log_trade_csv(simbol, tip, cantitate=0.0, pret=0.0, profit_pct=0.0):
    with open(TRADE_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            simbol,
            tip,
            f"{cantitate:.6f}",
            f"{pret:.2f}",
            f"{profit_pct:.2f}"
        ])

def init_signal_log():
    if not os.path.exists(SIGNAL_FILE):
        with open(SIGNAL_FILE, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Timp", "Simbol", "Semnal", "Preț", "RiskScore", "Volatilitate"])

def log_signal_csv(simbol, semnal, pret, scor, volatilitate):
    with open(SIGNAL_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            simbol,
            semnal,
            f"{pret:.2f}",
            f"{scor:.2f}",
            f"{volatilitate:.4f}"
        ])


# -------------------- LOGGING DB --------------------
def log_signal_db(simbol, semnal, pret, scor, volatilitate):
    try:
        cur.execute(
            "INSERT INTO signals (timestamp, symbol, signal, price, risk_score, volatility) VALUES (%s,%s,%s,%s,%s,%s)",
            (datetime.now(), simbol, semnal, pret, scor, volatilitate)
        )
        conn.commit()
    except Exception as e:
        print(f"[{datetime.now()}] ❌ Eroare log_signal_db: {e}")
        conn.rollback()

def log_trade_db(simbol, tip, cantitate, pret, profit_pct, status="EXECUTED"):
    try:
        cur.execute(
            "INSERT INTO trades (timestamp, symbol, action, quantity, price, profit_pct, status) VALUES (%s,%s,%s,%s,%s,%s,%s)",
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
    capital_total = float(balans.get("ZEUR", 0))
    for simbol in strategie.get("symbols", []):
        if simbol.endswith("ZEUR"):
            asset = simbol.replace("ZEUR", "")
            if asset in balans:
                try:
                    cantitate = float(balans[asset])
                    pret = get_price(simbol)
                    capital_total += cantitate * pret
                except Exception as e:
                    print(f"[{datetime.now()}] ⚠️ Eroare la calcul capital pentru {asset}: {e}")
    return capital_total


# -------------------- BOT LOOP --------------------
def ruleaza_bot():
    strategie = incarca_strategia()
    init_trade_log()
    init_signal_log()
    init_db()  # <<---- creează tabelele automat dacă lipsesc

    balans_initial = get_balance()
    capital_initial = calculeaza_capital_total(strategie, balans_initial)

    print(f"[{datetime.now()}] 🤖 Bot AI REAL pornit cu DB Postgres!")
    print(f"[{datetime.now()}] 💰 Capital inițial total detectat: {capital_initial:.2f} EUR")

    alocari_fix = {
        simbol: capital_initial * strategie.get("allocations", {}).get(simbol, 0.0)
        for simbol in strategie.get("symbols", ["XXBTZEUR"])
    }
    print(f"[{datetime.now()}] 📊 Alocări fixe (strict pe simbol): {alocari_fix}")

    pozitii = {
        simbol: {"deschis": False, "pret_intrare": 0, "cantitate": 0.0}
        for simbol in strategie.get("symbols", ["XXBTZEUR"])
    }

    while True:
        try:
            balans = get_balance()

            for simbol in strategie.get("symbols", ["XXBTZEUR"]):
                pret = get_price(simbol)
                semnal, scor, volatilitate = calculeaza_semnal(simbol, strategie)

                # logăm și în CSV și în DB
                log_signal_csv(simbol, semnal, pret, scor, volatilitate)
                log_signal_db(simbol, semnal, pret, scor, volatilitate)

                pozitie = pozitii[simbol]
                eur_alocat = alocari_fix.get(simbol, 0.0)

                if not pozitie["deschis"] and semnal == "BUY":
                    if float(balans.get("ZEUR", 0)) < eur_alocat * 0.99:
                        print(f"[{datetime.now()}] ⚠️ Fonduri insuficiente pentru {simbol} (alocat {eur_alocat:.2f} EUR).")
                        log_trade_csv(simbol, "IGNORED_BUY_NO_FUNDS", 0.0, pret, 0.0)
                        log_trade_db(simbol, "IGNORED_BUY_NO_FUNDS", 0.0, pret, 0.0, "IGNORED")
                        continue

                    if eur_alocat > 10:
                        cantitate = (eur_alocat * 0.99) / pret
                        response = place_market_order("buy", cantitate, simbol)
                        pozitie["pret_intrare"] = pret
                        pozitie["cantitate"] = cantitate
                        pozitie["deschis"] = True
                        print(f"[{datetime.now()}] ✅ BUY {simbol} la {pret:.2f} cu {eur_alocat:.2f} EUR (cantitate={cantitate:.6f})")
                        log_trade_csv(simbol, "BUY", cantitate, pret, 0.0)
                        log_trade_db(simbol, "BUY", cantitate, pret, 0.0)

                elif pozitie["deschis"]:
                    profit_pct = (pret - pozitie["pret_intrare"]) / pozitie["pret_intrare"] * 100

                    if profit_pct >= strategie["Take_Profit"]:
                        response = place_market_order("sell", pozitie["cantitate"], simbol)
                        pozitie["deschis"] = False
                        print(f"[{datetime.now()}] ✅ SELL {simbol} (TakeProfit) la {pret:.2f} | Profit={profit_pct:.2f}%")
                        log_trade_csv(simbol, "SELL_TP", pozitie["cantitate"], pret, profit_pct)
                        log_trade_db(simbol, "SELL_TP", pozitie["cantitate"], pret, profit_pct)

                    elif profit_pct <= -strategie["Stop_Loss"]:
                        response = place_market_order("sell", pozitie["cantitate"], simbol)
                        pozitie["deschis"] = False
                        print(f"[{datetime.now()}] ✅ SELL {simbol} (StopLoss) la {pret:.2f} | Profit={profit_pct:.2f}%")
                        log_trade_csv(simbol, "SELL_SL", pozitie["cantitate"], pret, profit_pct)
                        log_trade_db(simbol, "SELL_SL", pozitie["cantitate"], pret, profit_pct)

                    elif semnal == "BUY":
                        print(f"[{datetime.now()}] ⏭️ Semnal BUY ignorat pentru {simbol}, poziție deja deschisă.")
                        log_trade_csv(simbol, "IGNORED_BUY_ALREADY_OPEN", pozitie["cantitate"], pret, 0.0)
                        log_trade_db(simbol, "IGNORED_BUY_ALREADY_OPEN", pozitie["cantitate"], pret, 0.0, "IGNORED")

                print(f"[{datetime.now()}] 📈 {simbol} | Semnal={semnal} | Preț={pret:.2f} | RiskScore={scor:.2f} | Balans={balans}")

        except Exception as e:
            print(f"[{datetime.now()}] ❌ Eroare în rulare: {e}")

        time.sleep(10)


if __name__ == "__main__":
    print(f"[{datetime.now()}] 🚀 Bot pornit - versiune cu Postgres + CSV (auto-create tables)")
    init_db()
    ruleaza_bot()
