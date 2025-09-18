import krakenex

api = krakenex.API()

# Mapare pentru simboluri care nu corespund exact pe Kraken
SYMBOL_MAP = {
    "ADAEUR": "ADAXEUR",  # corectăm ADA
    "XETHZEUR": "ETHEUR",  # dacă mai apare și varianta asta
}

def normalize_symbol(symbol: str) -> str:
    """Normalizează simbolul pentru Kraken dacă e necesar"""
    return SYMBOL_MAP.get(symbol, symbol)

def get_price(symbol: str):
    """Obține prețul curent pentru un simbol de pe Kraken"""
    try:
        kraken_symbol = normalize_symbol(symbol)
        data = api.query_public("Ticker", {"pair": kraken_symbol})
        if "error" in data and data["error"]:
            print(f"❌ Eroare Kraken la {kraken_symbol}: {data['error']}")
            return None
        return float(data["result"][kraken_symbol]["c"][0])
    except Exception as e:
        print(f"[get_price] Eroare pentru {symbol}: {e}")
        return None

def place_market_order(symbol: str, side: str, volume: float):
    """Plasează un ordin de tip market"""
    try:
        kraken_symbol = normalize_symbol(symbol)
        order = {
            "pair": kraken_symbol,
            "type": side,
            "ordertype": "market",
            "volume": str(volume),
        }
        response = api.query_private("AddOrder", order)
        if response["error"]:
            print(f"❌ Eroare Kraken: {response['error']}")
            return None
        return response["result"]
    except Exception as e:
        print(f"[place_market_order] Eroare pentru {symbol}: {e}")
        return None
