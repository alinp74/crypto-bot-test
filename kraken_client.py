import os
import krakenex
from dotenv import load_dotenv
from pykrakenapi import KrakenAPI
import logging

# Încarcă variabilele din .env
load_dotenv()

# Configurează loggerul
logger = logging.getLogger(__name__)

# Inițializează API-ul Kraken
api = krakenex.API()
api.key = os.getenv('KRAKEN_API_KEY')
api.secret = os.getenv('KRAKEN_API_SECRET')
k = KrakenAPI(api)

def get_price(pair='XBTEUR'):
    try:
        ticker = k.get_ticker_information(pair)
        return float(ticker['c'][pair][0])  # Prețul de închidere (ultimul preț tranzacționat)
    except Exception as e:
        logger.error(f"Eroare la get_price: {e}")
        return 0.0

def get_balance(asset='XXBT'):
    try:
        balance = k.get_account_balance()
        return float(balance[asset])
    except Exception as e:
        logger.error(f"Eroare la get_balance: {e}")
        return 0.0

def place_market_order(pair='XBTEUR', side='buy', volume=0.0001):
    try:
        response = api.query_private('AddOrder', {
            'pair': pair,
            'type': side,
            'ordertype': 'market',
            'volume': str(volume),  # Kraken cere volume ca string
        })

        if response.get('error'):
            logger.error(f"❌ Eroare la plasarea ordinului: {response['error']}")
        else:
            logger.info(f"✅ Ordin {side.upper()} plasat: {volume} BTC")
        return response
    except Exception as e:
        logger.error(f"❌ Eroare generală la place_market_order: {e}")
        return None

# Doar pentru testare locală
if __name__ == "__main__":
    print("✅ Conectare reușită.")
    btc_balance = get_balance('XXBT')
    print(f"BTC balance: {btc_balance}")
    current_price = get_price()
    print(f"Preț curent BTC/EUR: {current_price}")
