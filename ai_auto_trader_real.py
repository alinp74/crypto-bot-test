import time
import json
import csv
import os
from datetime import datetime
from kraken_client import get_price, get_balance, place_market_order
from strategie import calculeaza_semnal  # strategia noastră

# Fișiere log
TRADE_FILE = "trades_log.csv"
SIGNAL_FILE = "signals_log.csv"


# -------------------- LOGGING --------------------
def init_trade_log():
    if not os.path.exists(TRADE_FILE):
        with open(TRADE_FILE, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Timp", "Simbol", "Tip", "Cantitate", "Preț", "Profit %"])

def log_trade(simbol, tip, cantitate, pret, profit_pct=0.0):
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

def log_signal(simbol, semnal, pret, scor, volatilitate):
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
            "allocations": {"XXBTZEUR": 1.0},  # fallback: tot capitalul pe BTC
            "RSI_Period": 7,
            "RSI_OB": 70,
            "RSI_OS": 30,
            "MACD_Fast": 12,
            "MACD_Slow": 26,
            "MACD_Signal": 9,
            "Stop_Loss": 1,
            "Take_Profit": 2.0,
            "Profit": 0,
            "Updated": str(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        }


# -------------------- CALCUL CAPITAL --------------------
def calculeaza_capital_total(strategie, balans):
    """Calculează capitalul total în EUR (cash + valoare crypto)."""
    capital_total = float(balans.get("ZEUR", 0))

    for simbol in strategie.get("symbols", []):
        if simbol.endswith("ZEUR"):  # ex: XXBTZEUR, XETHZEUR, ADAEUR
            asset = simbol.replace("ZEUR", "")  # XXBT, XETH, ADA
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

    balans_initial = get_balance()
    capital_initial = calculeaza_capital_total(strategie, balans_initial)

    print(f"[{datetime.now()}] 🤖 Bot AI REAL pornit!")
    print(f"[{datetime.now()}] 💰 Capital inițial total detectat: {capital_initial:.2f} EUR (inclusiv crypto)")
    
    # calculăm alocarea fixă pe monede (din capitalul inițial total)
    alocari_fix = {
        simbol: capital_initial * strategie.get("allocations", {}).get(simbol, 0.0)
        for simbol in strategie.get("symbols", ["XXBTZEUR"])
    }
    print(f"[{datetime.now()}] 📊 Alocări fixe: {alocari_fix}")

    # fiecare simbol are propria poziție
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
                log_signal(simbol, semnal, pret, scor, volatilitate)

                pozitie = pozitii[simbol]
                eur_alocat = alocari_fix.get(simbol, 0.0)

                if not pozitie["deschis"] and semnal == "BUY":
                    if eur_alocat > 10:  # minim pentru Kraken
                        cantitate = eur_alocat / pret
                        response = place_market_order("buy", cantitate, simbol)
                        pozitie["pret_intrare"] = pret
                        pozitie["cantitate"] = cantitate
                        pozitie["deschis"] = True
                        print(f"[{datetime.now()}] ✅ BUY {simbol} la {pret} cu {eur_alocat:.2f} EUR")
                        log_trade(simbol, "BUY", cantitate, pret)

                elif pozitie["deschis"]:
                    profit_pct = (pret - pozitie["pret_intrare"]) / pozitie["pret_intrare"] * 100
                    if profit_pct >= strategie["Take_Profit"] or semnal == "SELL":
                        response = place_market_order("sell", pozitie["cantitate"], simbol)
                        pozitie["deschis"] = False
                        print(f"[{datetime.now()}] ✅ SELL {simbol} la {pret} | Profit={profit_pct:.2f}%")
                        log_trade(simbol, "SELL", pozitie["cantitate"], pret, profit_pct)

                print(f"[{datetime.now()}] 📈 {simbol} | Semnal={semnal} | Preț={pret:.2f} | RiskScore={scor:.2f} | Vol={volatilitate:.4f} | EUR_Alocat_Fix={eur_alocat:.2f} | Balans={balans}")

        except Exception as e:
            print(f"[{datetime.now()}] ❌ Eroare în rulare: {e}")

        time.sleep(10)


if __name__ == "__main__":
    print(f"[{datetime.now()}] 🚀 Bot pornit - versiune cu capital total (EUR + crypto) pentru alocări fixe")
    ruleaza_bot()
