import os
import time
import json
import datetime
from kraken_client import set_credentials, get_balance, get_price, place_market_order
from strategie import semnal_tranzactionare

# ================== CONFIG ==================
API_KEY = os.getenv("KRAKEN_API_KEY")
API_SECRET = os.getenv("KRAKEN_API_SECRET")
set_credentials(API_KEY, API_SECRET)

# Perechi de tranzacționare
SYMBOLS = ["XXBTZEUR", "ADAEUR", "XETHZEUR"]
ALLOCATIONS = {"XXBTZEUR": 0.33, "ADAEUR": 0.33, "XETHZEUR": 0.34}

# ================== BOT LOOP ==================
print(f"[{datetime.datetime.now()}] 🚀 Bot started (safe trading mode)...")

while True:
    try:
        balans = get_balance()
        print(f"[{datetime.datetime.now()}] 🔎 Balans: {balans}")

        for pair in SYMBOLS:
            price = get_price(pair)
            if not price:
                continue

            # Pregătim un DataFrame fictiv pentru strategie (se poate schimba cu OHLC real)
            import pandas as pd
            df = pd.DataFrame({"close": [price] * 50})
            signal = semnal_tranzactionare(df)

            print(f"[{datetime.datetime.now()}] 📈 {pair} | Semnal={signal} | Preț={price}")

            if signal in ["BUY", "SELL"]:
                # Calcul volum în funcție de alocare și balanță
                eur_total = float(balans.get("ZEUR", 0))
                alloc_eur = eur_total * ALLOCATIONS[pair]
                if alloc_eur <= 0:
                    continue

                volume = alloc_eur / price

                response = place_market_order(pair, signal.lower(), volume)
                if "error" in response and response["error"]:
                    print(f"[{datetime.datetime.now()}] ❌ Eroare execuție: {response['error']}")
                else:
                    print(f"[{datetime.datetime.now()}] ✅ Ordin {signal} {pair} executat: {response}")

        time.sleep(30)

    except Exception as e:
        print(f"[{datetime.datetime.now()}] ❌ Eroare în rulare: {e}")
        time.sleep(10)
