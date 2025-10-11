import time
import traceback
from datetime import datetime
from decimal import Decimal
from kraken_client import k
from strategie import calculeaza_semnal
from db_manager import salveaza_pret, salveaza_semnal, salveaza_tranzactie, get_pozitii_deschise, update_pozitie
from strategy_loader import incarca_strategie
from utils import calculeaza_profit, calculeaza_balanta

# ✅ Config
DCA_DROP_PCT = 3.0     # scădere minimă pentru DCA
MIN_ORDER_EUR = {"XXBTZEUR": 20.0, "XETHZEUR": 20.0}  # praguri minime
LOOP_INTERVAL = 10     # secunde între cicluri

def place_market_order(side, volume, pair):
    try:
        resp = k.add_order(pair=pair, type=side, ordertype="market", volume=volume)
        if resp["error"]:
            raise Exception(f"[place_market_order] Eroare Kraken: {resp['error']}")
        txid = resp["result"]["txid"][0]
        print(f"[{datetime.now()}] ✅ Order executat {side.upper()} {pair}: {volume} (txid={txid})")
        return True
    except Exception as e:
        print(f"[{datetime.now()}] ❌ Eroare order: {e}")
        return False

def ruleaza_bot():
    print(f"[{datetime.now()}] 🚀 Bot trading pornit!")

    strategie = incarca_strategie()
    pozitii = get_pozitii_deschise()

    balans_initial = calculeaza_balanta(k)
    print(f"[{datetime.now()}] 🔎 Balans inițial: {balans_initial}")

    while True:
        try:
            for simbol in strategie["symbols"]:
                pret = k.get_ticker_price(simbol)
                salveaza_pret(simbol, pret)

                semnal, scor, volatilitate = calculeaza_semnal(simbol, strategie)
                salveaza_semnal(simbol, semnal)

                # 🔍 Găsim poziția actuală
                poz = pozitii.get(simbol)
                if not poz:
                    continue

                profit_pct, profit_eur = calculeaza_profit(poz, pret)
                print(f"[{datetime.now()}] 🧪 {simbol}: profit={profit_pct:.2f}% | max={poz.get('profit_max', 0):.2f}% | qty={poz['cantitate']}")

                # ✅ DCA / SL logic actualizată
                if poz["deschis"]:
                    drop_pct = ((poz["pret_intrare"] - pret) / poz["pret_intrare"]) * 100.0

                    # 🟡 1️⃣ Stop-Loss prioritar
                    if profit_pct <= -float(strategie.get("Stop_Loss", 7.0)):
                        print(f"[{datetime.now()}] 🛑 Stop-Loss activ: {profit_pct:.2f}% → SELL")
                        ok = place_market_order("sell", poz["cantitate"], simbol)
                        if ok:
                            update_pozitie(simbol, "inchisa", pret, profit_eur)
                            salveaza_tranzactie(simbol, "SELL_SIGNAL", poz["cantitate"], pret, profit_eur)
                        continue

                    # 🟢 2️⃣ DCA doar dacă nu e sub SL și există fonduri
                    elif drop_pct >= DCA_DROP_PCT and profit_pct > -float(strategie.get("Stop_Loss", 7.0)):
                        eur_avail = balans_initial.get("ZEUR", 0.0)
                        if eur_avail < MIN_ORDER_EUR.get(simbol, 20.0):
                            print(f"[{datetime.now()}] ⚠️ Fonduri insuficiente pentru DCA {simbol} — sar peste și verific SL.")
                            continue

                        vol_dca = poz["cantitate"] * Decimal("0.3")  # 30% din cantitatea inițială
                        print(f"[{datetime.now()}] 🔄 DCA BUY: {simbol} +{vol_dca} @ {pret}")
                        ok = place_market_order("buy", vol_dca, simbol)
                        if ok:
                            salveaza_tranzactie(simbol, "DCA_BUY", vol_dca, pret, 0)

                # 🔁 BUY principal
                if semnal == "BUY" and not poz["deschis"]:
                    eur_avail = balans_initial.get("ZEUR", 0.0)
                    eur_alocat = eur_avail * strategie["allocations"].get(simbol, 0.5)
                    if eur_alocat < MIN_ORDER_EUR.get(simbol, 20.0):
                        continue
                    volume = eur_alocat / pret
                    ok = place_market_order("buy", volume, simbol)
                    if ok:
                        salveaza_tranzactie(simbol, "BUY", volume, pret, 0)
                        pozitii[simbol] = {"cantitate": volume, "pret_intrare": pret, "deschis": True}

                # 🔁 SELL principal
                elif semnal == "SELL" and poz["deschis"]:
                    ok = place_market_order("sell", poz["cantitate"], simbol)
                    if ok:
                        salveaza_tranzactie(simbol, "SELL_SIGNAL", poz["cantitate"], pret, profit_eur)
                        update_pozitie(simbol, "inchisa", pret, profit_eur)

            time.sleep(LOOP_INTERVAL)

        except Exception as e:
            print(f"[{datetime.now()}] ❌ Loop error: {e}")
            traceback.print_exc()
            time.sleep(10)

if __name__ == "__main__":
    ruleaza_bot()
