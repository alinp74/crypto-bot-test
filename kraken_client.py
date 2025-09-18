import krakenex
from pykrakenapi import KrakenAPI
import time

# Inițializează conexiunea
api = krakenex.API()
k = KrakenAPI(api)

# Funcție pentru prețul curent
def get_price(symbol):
    try:
        data = api.query_public("Ticker", {"pair": symbol})
        result = data.get("result", {})
        if not result:
            raise ValueError("No result in Kraken response")

        # Kraken returnează un dict cu cheia = symbol
        ticker = list(result.values())[0]
        price = float(ticker["c"][0])  # 'c' = last trade closed price
        return price
    except Exception as e:
        print(f"[get_price] Eroare: {e}")
        return None

# Funcție pentru OHLC (date istorice)
def get_ohlc(symbol, interval=5):
    try:
        ohlc, _ = k.get_ohlc_data(symbol, interval=interval)
        return ohlc
    except Exception as e:
        print(f"[get_ohlc] Eroare: {e}")
        return None

# Funcție pentru plasarea ordinelor de tip market
def place_market_order(symbol, side, volume):
    try:
        # Respectăm limita minimă Kraken
        if volume <= 0:
            raise ValueError("Volume must be greater than 0")

        # Trimitere ordin
        print(f"[place_market_order] Trimit {side} {volume} {symbol}")
        resp = api.query_private(
            "AddOrder",
            {
                "pair": symbol,
                "type": side,
                "ordertype": "market",
                "volume": str(volume),
            },
        )

        # Verificare răspuns
        if resp.get("error"):
            raise Exception(f"[place_market_order] Eroare Kraken: {resp['error']}")

        return resp
    except Exception as e:
        print(f"[place_market_order] Eroare: {e}")
        return None
