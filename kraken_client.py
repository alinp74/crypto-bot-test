import krakenex
from pykrakenapi import KrakenAPI
import datetime as dt

# Client global
api = krakenex.API()
k = KrakenAPI(api)

# Normalizare simboluri
def normalize_symbol(symbol: str) -> str:
    mapping = {
        "BTC": "XXBTZEUR",
        "ETH": "XETHZEUR",
        "ADA": "ADAEUR",
        "XXBTZEUR": "XXBTZEUR",
        "XETHZEUR": "XETHZEUR",
        "ADAEUR": "ADAEUR"
    }
    return mapping.get(symbol, symbol)

def get_price(symbol: str, client=None):
    """Returnează (timestamp, price) pentru un simbol"""
    try:
        kraken_symbol = normalize_symbol(symbol)

        if isinstance(client, KrakenAPI):
            # Folosește pykrakenapi
            ohlc, _ = client.get_ohlc_data(kraken_symbol, interval=1, ascending=True)
            last_row = ohlc.iloc[-1]
            price = float(last_row["close"])
            ts = dt.datetime.utcnow()
            return ts, price

        else:
            # Fallback la krakenex API
            api_client = client if client else api
            data = api_client.query_public("Ticker", {"pair": kraken_symbol})
            if "error" in data and data["error"]:
                print(f"❌ Eroare Kraken la {kraken_symbol}: {data['error']}")
                return None, None
            price = float(data["result"][kraken_symbol]["c"][0])
            ts = dt.datetime.utcnow()
            return ts, price

    except Exception as e:
        print(f"[get_price] Eroare pentru {symbol}: {e}")
        return None, None

def place_market_order(symbol: str, side: str, volume: float):
    """Plasează ordin market pe Kraken"""
    try:
        kraken_symbol = normalize_symbol(symbol)
        order = {
            "pair": kraken_symbol,
            "type": side,
            "ordertype": "market",
            "volume": str(volume)
        }
        response = api.query_private("AddOrder", order)
        if "error" in response and response["error"]:
            print(f"❌ Eroare Kraken: {response['error']}")
            return None
        return response["result"]
    except Exception as e:
        print(f"[place_market_order] Eroare: {e}")
        return None
