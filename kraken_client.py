import krakenex
from pykrakenapi import KrakenAPI

api = krakenex.API()
k = KrakenAPI(api)

def set_credentials(api_key, api_secret):
    api.key = api_key
    api.secret = api_secret

def get_balance():
    return k.get_account_balance().to_dict()['vol']

def get_price(pair):
    try:
        data = api.query_public('Ticker', {'pair': pair})
        return float(data['result'][pair]['c'][0])
    except Exception as e:
        print(f"[get_price] Eroare: {e}")
        return None

def place_market_order(pair, side, volume):
    """Execută ordine pe Kraken cu verificarea volumului minim."""
    try:
        # Volumul minim depinde de pereche
        min_volume = {
            "XXBTZEUR": 0.0002,   # BTC
            "ADAEUR": 5.0,        # ADA
            "XETHZEUR": 0.01      # ETH
        }

        if pair in min_volume and volume < min_volume[pair]:
            return {"error": [f"Volume {volume} sub minimul acceptat pentru {pair} ({min_volume[pair]})"]}

        order = api.query_private('AddOrder', {
            'pair': pair,
            'type': side,
            'ordertype': 'market',
            'volume': volume
        })
        return order
    except Exception as e:
        return {"error": [f"[place_market_order] Eroare: {str(e)}"]}
