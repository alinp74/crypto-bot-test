import os
import krakenex
from pykrakenapi import KrakenAPI

api = krakenex.API()
api_key = os.getenv('KRAKEN_API_KEY')
api_secret = os.getenv('KRAKEN_API_SECRET')

if not api_key or not api_secret:
    raise ValueError("❌ Cheile KRAKEN_API_KEY sau KRAKEN_API_SECRET lipsesc din environment!")

api.key = api_key
api.secret = api_secret
k = KrakenAPI(api)

def get_price(pair='XXBTZEUR'):
    try:
        ohlc, last = k.get_ohlc_data(pair, interval=1)
        price = ohlc['close'].iloc[-1]
        return float(price)
    except Exception as e:
        print(f"[get_price] Eroare: {e}")
        return None

def get_balance():
    try:
        balances = k.get_account_balance()
        return balances.to_dict()['vol']
    except Exception as e:
        print(f"[get_balance] Eroare: {e}")
        return {}

def place_market_order(pair='XXBTZEUR', type='buy', volume='0.001'):
    try:
        response = api.query_private('AddOrder', {
            'pair': pair,
            'type': type,
            'ordertype': 'market',
            'volume': volume,
        })
        return response
    except Exception as e:
        print(f"[place_market_order] Eroare: {e}")
        return None