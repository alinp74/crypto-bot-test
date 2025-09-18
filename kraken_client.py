import krakenex
from pykrakenapi import KrakenAPI

# Conexiune la Kraken
api = krakenex.API()
k = KrakenAPI(api)


def get_price(symbol):
    """Preia prețul de pe Kraken pentru simbolul dat"""
    try:
        data = k.get_ticker_information(symbol)
        # "c" = last trade closed [price, lot volume]
        price = float(data[symbol]["c"][0])
        return price
    except Exception as e:
        print(f"[get_price] Eroare pentru {symbol}: {e}")
        return None


def place_market_order(symbol, side, volume):
    """Plasează un ordin de tip market"""
    try:
        order = api.query_private(
            "AddOrder",
            {
                "pair": symbol,
                "type": side,
                "ordertype": "market",
                "volume": str(volume),
            },
        )
        if order.get("error"):
            raise Exception(f"[place_market_order] Eroare Kraken: {order['error']}")
        return order
    except Exception as e:
        print(f"[place_market_order] Eroare: {e}")
        return None
