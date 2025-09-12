import krakenex
from pykrakenapi import KrakenAPI
import os

api_key = os.getenv("KRAKEN_API_KEY")
api_secret = os.getenv("KRAKEN_API_SECRET")

if not api_key or not api_secret:
    raise ValueError("❌ Cheile KRAKEN_API_KEY sau KRAKEN_API_SECRET lipsesc din environment!")

api = krakenex.API(key=api_key, secret=api_secret)
k = KrakenAPI(api)

def get_price(pair='XXBTZEUR'):
    try:
        data = k.get_ticker_information(pair)
        return float(data['c'][0])
    except Exception as e:
        raise RuntimeError(f"[get_price] Eroare: {e}")

def get_balance():
    try:
        balances = k.get_account_balance()
        return balances.to_dict()['vol']
    except Exception as e:
        raise RuntimeError(f"[get_balance] Eroare: {e}")

def place_market_order(side="buy", volume=0.001, pair="XXBTZEUR"):
    try:
        order_type = "market"
        response = api.query_private("AddOrder", {
            "pair": pair,
            "type": side,
            "ordertype": order_type,
            "volume": str(volume)
        })
        return response
    except Exception as e:
        raise RuntimeError(f"[place_market_order] Eroare: {e}")
