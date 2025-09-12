import time
import json
import csv
import os
from datetime import datetime
from kraken_client import get_price, get_balance, place_market_order
from strategie import calculeaza_semnal  # strategia noastră

LOG_FILE = "trades_log.csv"

def init_log():
    """Creează fișierul CSV dacă nu există."""
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Timp", "Tip", "Cantitate", "Preț", "Profit %"])

def log_trade(tip, cantitate, pret, profit_pct=0.0):
    """Scrie un trade în fișierul CSV."""
    with open(LOG_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            tip,
            f"{cantitate:.6f}",
            f"{pret:.2f}",
            f"{profit_pct:.2f}"
        ])

def incarca_strategia():
    try:
        with open("strategy.json", "r") as f:
            strategie = json.load(f)
        print(f"[{datetime.now()}] ✅ Strategie încărcată: {strategie}")
        return strategie
    except Exception as e:
        print(f"[{datetime.now()}] ❌ Eroare la încărcarea strategiei: {e}")
        return {
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

def ruleaza_bot():
    strategie = incarca_strategia()
    init_log()
    print(f"[{datetime.now()}] 🤖 Bot AI REAL pornit! Strategia optimă: {strategie}")

    pozitie_deschisa = False
    pret_intrare = 0
    cantitate = 0.0
    simbol = "XXBTZEUR"

    while True:
        try:
            pret = get_price(simbol)
            balans = get_balance()
            semnal, scor, volatilitate = calculeaza_semnal(simbol, strategie)

            if not pozitie_deschisa and semnal == "BUY":
                eur_disponibil = float(balans.get("ZEUR", 0))
                if eur_disponibil > 10:  # minim pentru Kraken
                    cantitate = eur_disponibil / pret
                    place_market_order("buy", cantitate, simbol)
                    pret_intrare = pret
                    pozitie_deschisa = True
                    print(f"[{datetime.now()}] ✅ Ordin BUY executat la {pret}")
                    log_trade("BUY", cantitate, pret)

            elif pozitie_deschisa:
                profit_pct = (pret - pret_intrare) / pret_intrare * 100

                if profit_pct >= strategie["Take_Profit"] or semnal == "SELL":
                    place_market_order("sell", cantitate, simbol)
                    pozitie_deschisa = False
                    print(f"[{datetime.now()}] ✅ Ordin SELL executat la {pret} | Profit={profit_pct:.2f}%")
                    log_trade("SELL", cantitate, pret, profit_pct)

            print(f"[{datetime.now()}] 📈 Semnal={semnal} | Preț={pret:.2f} | RiskScore={scor:.2f} | Vol={volatilitate:.4f} | Balans={balans}")

        except Exception as e:
            print(f"[{datetime.now()}] ❌ Eroare în rulare: {e}")

        time.sleep(10)

if __name__ == "__main__":
    ruleaza_bot()
