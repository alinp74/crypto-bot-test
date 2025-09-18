import krakenex
from pykrakenapi import KrakenAPI

# Client Kraken global
api = krakenex.API()
k = KrakenAPI(api)

# Normalizare simboluri pentru Kraken
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
    """Obține prețul curent pentru un simbol de pe Kraken"""
    try:
        kraken_symbol = normalize_symbol(symbol)
        api_client = client if client else api
        data = api_client.query_public("Ticker", {"pair": kraken_symbol})
        if "error" in data and data["error"]:
            print(f"❌ Eroare Kraken la {kraken_symbol}: {data['error']}")
            return None
        return float(data["result"][kraken_symbol]["c"][0])
    except Exception as e:
        print(f"[get_price] Eroare pentru {symbol}: {e}")
        return None

def place_market_order(symbol: str, side: str, volume: float):
    """Plasează un ordin de tip market pe Kraken"""
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
