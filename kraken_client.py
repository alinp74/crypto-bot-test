ddef get_price(symbol):
    """Preia prețul de pe Kraken pentru simbolul dat"""
    try:
        data = k.get_ticker_information(symbol)
        # Extragem corect prețul de închidere ("c" este lista [price, lot volume])
        price = float(data[symbol]["c"][0])
        return price
    except Exception as e:
        print(f"[get_price] Eroare pentru {symbol}: {e}")
        return None

 def get_price(symbol):
    """Preia prețul de pe Kraken pentru simbolul dat"""
    try:
        data = k.get_ticker_information(symbol)
        # Extragem corect prețul de închidere ("c" este lista [price, lot volume])
        price = float(data[symbol]["c"][0])
        return price
    except Exception as e:
        print(f"[get_price] Eroare pentru {symbol}: {e}")
        return None
l."""
 def get_price(symbol):
    """Preia prețul de pe Kraken pentru simbolul dat"""
    try:
        data = k.get_ticker_information(symbol)
        # Extragem corect prețul de închidere ("c" este lista [price, lot volume])
        price = float(data[symbol]["c"][0])
        return price
    except Exception as e:
        print(f"[get_price] Eroare pentru {symbol}: {e}")
        return None

 def get_price(symbol):
    """Preia prețul de pe Kraken pentru simbolul dat"""
    try:
        data = k.get_ticker_information(symbol)
        # Extragem corect prețul de închidere ("c" este lista [price, lot volume])
        price = float(data[symbol]["c"][0])
        return price
    except Exception as e:
        print(f"[get_price] Eroare pentru {symbol}: {e}")
        return None

 def get_price(symbol):
    """Preia prețul de pe Kraken pentru simbolul dat"""
    try:
        data = k.get_ticker_information(symbol)
        # Extragem corect prețul de închidere ("c" este lista [price, lot volume])
        price = float(data[symbol]["c"][0])
        return price
    except Exception as e:
        print(f"[get_price] Eroare pentru {symbol}: {e}")
        return None

 def get_price(symbol):
    """Preia prețul de pe Kraken pentru simbolul dat"""
    try:
        data = k.get_ticker_information(symbol)
        # Extragem corect prețul de închidere ("c" este lista [price, lot volume])
        price = float(data[symbol]["c"][0])
        return price
    except Exception as e:
        print(f"[get_price] Eroare pentru {symbol}: {e}")
        return None

 def get_price(symbol):
    """Preia prețul de pe Kraken pentru simbolul dat"""
    try:
        data = k.get_ticker_information(symbol)
        # Extragem corect prețul de închidere ("c" este lista [price, lot volume])
        price = float(data[symbol]["c"][0])
        return price
    except Exception as e:
        print(f"[get_price] Eroare pentru {symbol}: {e}")
        return None



def place_market_order(api, pair: str, side: str, volume: float):
    """Trimite un ordin de tip market pe Kraken."""
    try:
        resp = api.query_private(
            "AddOrder",
            {
                "pair": pair,
                "type": side,
                "ordertype": "market",
                "volume": str(volume),
            },
        )
        if resp.get("error"):
            raise RuntimeError(f"[place_market_order] Eroare Kraken: {resp['error']}")
        return resp
    except Exception as e:
        raise RuntimeError(f"[place_market_order] Eroare: {e}")
