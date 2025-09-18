import krakenex
from pykrakenapi import KrakenAPI

# Client Kraken
api = krakenex.API()
k = KrakenAPI(api)

def get_price(symbol, config=None):
    """
    Returnează ultimul preț pentru o pereche de pe Kraken.
    Ignoră parametrii suplimentari.
    """
    try:
        data = k.get_ticker_information(symbol)
        price = float(data["c"].values[0][0])  # "c" = last trade closed
        return price
    except Exception as e:
        print(f"[get_price] Eroare pentru {symbol}: {e}")
        return None


def place_market_order(symbol, side, volume):
    """
    Simulare ordin market pe Kraken.
    În versiunea reală trebuie să folosim api.query_private('AddOrder', {...})
    """
    try:
        print(f"🔍 Kraken AddOrder request: side={side}, volume={volume}, pair={symbol}")
        response = {"descr": f"Simulated {side} {volume} {symbol}", "error": []}
        print(f"🔍 Kraken AddOrder response: {response}")
        return response
    except Exception as e:
        print(f"[place_market_order] Eroare: {e}")
        return {"error": [str(e)]}
