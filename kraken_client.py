import logging
import os
import krakenex

api = krakenex.API()

# Încarcă API key și secret din variabile de mediu (pentru Railway)
api.key = os.getenv("KRAKEN_API_KEY")
api.secret = os.getenv("KRAKEN_API_SECRET")

def get_price(pair='XXBTZEUR'):
    try:
        ticker = api.query_public('Ticker', {'pair': pair})
        logging.info(f"[get_price] Chei returnate de Kraken: {list(ticker['result'].keys())}")
        
        pair_data = list(ticker['result'].items())[0]
        _, data = pair_data
        
        price = float(data['c'][0])  # Ultimul preț
        return price
    except Exception as e:
        logging.error(f"[get_price] Eroare: {e}")
        return None

def get_balance(asset='XXBT'):
    try:
        balance = api.query_private('Balance')
        return float(balance['result'].get(asset, 0.0))
    except Exception as e:
        logging.error(f"[get_balance] Eroare: {e}")
        return 0.0

def place_market_order(side, pair='XXBTZEUR', volume=0.0001):
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
