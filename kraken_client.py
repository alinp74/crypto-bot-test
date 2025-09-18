import krakenex
from pykrakenapi import KrakenAPI
import os
from datetime import datetime

# Cheile API sunt luate din environment variables
api_key = os.getenv("KRAKEN_API_KEY")
api_secret = os.getenv("KRAKEN_API_SECRET")

if not api_key or not api_secret:
    raise ValueError("❌ Lipsesc cheile KRAKEN_API_KEY și KRAKEN_API_SECRET!")

api = krakenex.API(key=api_key, secret=api_secret)
k = KrakenAPI(api)

def get_price(pair='XXBTZEUR'):
    try:
        data = k.get_ticker_information(pair)
        # "c" = [last_trade_price, lot_volume]
        pret = data["c"].iloc[0][0]
        return float(pret)
    except Exception as e:
        raise RuntimeError(f"[get_price] Eroare: {e}")

def get_balance():
    try:
        balances = k.get_account_balance()
        return balances["vol"].to_dict()
    except Exception as e:
        raise RuntimeError(f"[get_balance] Eroare: {e}")

def place_market_order(side="buy", volume=0.001, pair="XXBTZEUR"):
    try:
        # Precizie corectă pentru Kraken (max 8 zecimale)
        volume_str = f"{volume:.8f}"

        response = api.query_private("AddOrder", {
            "pair": pair,
            "type": side,
            "ordertype": "market",
            "volume": volume_str
        })

        # Log prietenos
        if response.get("error"):
            print(f"[{datetime.now()}] ❌ Kraken order error: {response['error']}")
            raise RuntimeError(f"[place_market_order] Eroare Kraken: {response['error']}")
        else:
            descr = response.get("result", {}).get("descr", {}).get("order", "")
            txid = response.get("result", {}).get("txid", [""])[0]
            print(f"[{datetime.now()}] ✅ ORDIN EXECUTAT: {descr} | TXID={txid}")

        return response
    except Exception as e:
        raise RuntimeError(f"[place_market_order] Eroare: {e}")
