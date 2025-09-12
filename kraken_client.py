import krakenex
from pykrakenapi import KrakenAPI
import os

# Cheile API sunt luate din Railway Environment Variables
api_key = os.getenv("KRAKEN_API_KEY")
api_secret = os.getenv("KRAKEN_API_SECRET")

if not api_key or not api_secret:
    raise ValueError("❌ Lipsesc cheile KRAKEN_API_KEY și KRAKEN_API_SECRET din Railway Environment!")

api = krakenex.API(key=api_key, secret=api_secret)
k = KrakenAPI(api)

def get_price(pair='XXBTZEUR'):
    """
    Returnează ultimul preț de tranzacționare pentru un pair (ex. BTC/EUR).
    """
    try:
        data = k.get_ticker_information(pair)
        # "c" = [last_trade_price, lot_volume]
        pret = data["c"].iloc[0][0]  
        return float(pret)
    except Exception as e:
        raise RuntimeError(f"[get_price] Eroare: {e}")

def get_balance():
    """
    Returnează balanța contului ca dict {moneda: volum}.
    """
    try:
        balances = k.get_account_balance()
        return balances["vol"].to_dict()
    except Exception as e:
        raise RuntimeError(f"[get_balance] Eroare: {e}")

def place_market_order(side="buy", volume=0.001, pair="XXBTZEUR"):
    """
    Plasează un ordin de tip market pe Kraken.
    """
    try:
        response = api.query_private("AddOrder", {
            "pair": pair,
            "type": side,
            "ordertype": "market",
            "volume": str(volume)
        })
        if response.get("error"):
            raise RuntimeError(response["error"])
        return response
    except Exception as e:
        raise RuntimeError(f"[place_market_order] Eroare: {e}")
