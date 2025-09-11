import os
import krakenex
import logging

api = krakenex.API()

# Load API keys from environment variables (Railway friendly)
api.key = os.getenv('KRAKEN_API_KEY')
api.secret = os.getenv('KRAKEN_API_SECRET')

def get_price(pair='XBTEUR'):
    try:
        response = api.query_public('Ticker', {'pair': pair})
        ticker = response['result'][pair]
        return float(ticker['c'][0])  # Prețul curent (last closed price)
    except Exception as e:
        logging.error(f"[get_price] Eroare: {e}")
        return 0.0

def get_balance(asset='XXBT'):
    try:
        response = api.query_private('Balance')
        balance = response['result'].get(asset, 0.0)
        return float(balance)
    except Exception as e:
        logging.error(f"[get_balance] Eroare: {e}")
        return 0.0

def place_market_order(pair='XBTEUR', side='buy', volume=0.0001):
    try:
        order = {
            'pair': pair,
            'type': side,
            'ordertype': 'market',
            'volume': str(volume),
        }
        response = api.query_private('AddOrder', order)
        
        if response.get('error'):
            raise Exception(response['error'])

        logging.info(f"✅ Ordin {side.upper()} plasat: {volume} BTC")
        return response
    except Exception as e:
        logging.error(f"❌ Eroare la plasarea ordinului: {e}")
        return None
