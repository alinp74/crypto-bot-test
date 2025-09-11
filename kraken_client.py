import os
import krakenex
from pykrakenapi import KrakenAPI

api = krakenex.API()
api.key = os.getenv("KRAKEN_API_KEY")
api.secret = os.getenv("KRAKEN_API_SECRET")
k = KrakenAPI(api)


# Load API keys from environment variables (Railway friendly)
api.key = os.getenv('KRAKEN_API_KEY')
api.secret = os.getenv('KRAKEN_API_SECRET')

def get_price(pair='XBTEUR'):
    try:
        response = api.query_public('Ticker', {'pair': pair})
        
        # Afisam cheia exactă returnată de Kraken pentru debugging
        result_keys = list(response.get('result', {}).keys())
        logging.info(f"[get_price] Chei returnate de Kraken: {result_keys}")

        if not result_keys:
            raise ValueError("Nu s-au returnat rezultate din API.")
        
        # Folosim prima cheie, indiferent de nume (ex: 'XXBTZEUR' etc)
        ticker = response['result'][result_keys[0]]
        return float(ticker['c'][0])  # Prețul curent (last closed)
    
    except Exception as e:
        logging.error(f"[get_price] Eroare: {e}")
        return 0.0


def get_balance():
    try:
        if not api.key or not api.secret:
            raise Exception("Either key or secret is not set!")
        balance = k.get_account_balance()
        btc_balance = float(balance.loc['XXBT']['vol']) if 'XXBT' in balance.index else 0.0
        return btc_balance
    except Exception as e:
        logging.info(f"[get_balance] Eroare: {e}")
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
