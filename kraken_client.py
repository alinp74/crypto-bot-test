import os
import krakenex
import time
import logging

api = krakenex.API()

# Inițializează cheile direct din variabilele de mediu
api_key = os.getenv('KRAKEN_API_KEY')
api_secret = os.getenv('KRAKEN_API_SECRET')

if not api_key or not api_secret:
    raise ValueError("❌ Cheile KRAKEN_API_KEY sau KRAKEN_API_SECRET lipsesc din environment!")

api.key = api_key
api.secret = api_secret

def get_price(pair='XXBTZEUR'):
    try:
        response = api.query_public('Ticker', {'pair': pair})
        result = response.get('result', {})
        logging.info(f"[get_price] Chei returnate de Kraken: {list(result.keys())}")
        price_data = list(result.values())[0]
        price = float(price_data['c'][0])
        return price
    except Exception as e:
        logging.error(f"[get_price] Eroare: {e}")
        return None

def get_balance(*args, **kwargs):
    try:
        response = api.query_private('Balance')
        return response['result']
    except Exception as e:
        print(f"[get_balance] Eroare: {e}")
        return {}


def place_market_order(pair='XXBTZEUR', side='buy', volume=0.0001):
    try:
        order = {
            'pair': pair,
            'type': side,
            'ordertype': 'market',
            'volume': str(volume)
        }
        response = api.query_private('AddOrder', order)
        return response.get('result', {})
    except Exception as e:
        logging.error(f"[place_market_order] Eroare: {e}")
        return {}
