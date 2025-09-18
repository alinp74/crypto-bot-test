import krakenex
from pykrakenapi import KrakenAPI
import time

# Client Kraken
api = krakenex.API()
k = KrakenAPI(api)

# Mapare simboluri interne -> simboluri acceptate de Kraken
SYMBOL_MAP = {
    "XXBTZEUR": "XXBTZEUR",  # Bitcoin / Euro
    "XETHZEUR": "XETHZEUR",  # Ethereum / Euro
    "ADAEUR": "ADAEUR"       # Cardano / Euro
}

# =====================================================================
# Obține prețul curent
# =====================================================================
def get_price(symbol, config=None):
    try:
        kraken_symbol = SYMBOL_MAP.get(symbol, symbol)
        data = k.get_ticker_information(kraken_symbol)
        price = float(data["c"].values[0][0])  # "c" = last trade closed
        return price
    except Exception as e:
        print(f"[get_price] Eroare pentru {symbol}: {e}")
        return None

# =====================================================================
# Plasează ordine pe piață
# =====================================================================
def place_market_order(symbol, side, volume):
    try:
        kraken_symbol = SYMBOL_MAP.get(symbol, symbol)
        response = api.query_private(
            'AddOrder',
            {
                'pair': kraken_symbol,
                'type': side.lower(),
                'ordertype': 'market',
                'volume': str(volume)
            }
        )

        if response.get("error"):
            print(f"[place_market_order] Eroare Kraken: {response['error']}")
            return None
        else:
            print(f"[place_market_order] Succes: {response}")
            return response
    except Exception as e:
        print(f"[place_market_order] Eroare: {e}")
        return None
