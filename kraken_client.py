import os
import krakenex
from dotenv import load_dotenv
from pykrakenapi import KrakenAPI
import logging

# Configurare loguri
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s')

# Încarcă variabilele din .env
load_dotenv()

# Inițializează API-ul
api = krakenex.API()
api.key = os.getenv('KRAKEN_API_KEY')
api.secret = os.getenv('KRAKEN_API_SECRET')

# Conectează la Kraken API
try:
    k = KrakenAPI(api)
    logging.info("✅ Conectare reușită.")
except Exception as e:
    logging.error(f"❌ Eroare la conectare: {e}")
    exit()

# Returnează prețul curent BTC/EUR
def get_price(pair='XBTEUR'):
    try:
        ticker = k.get_ticker_information(pair)
        return float(ticker['c'][0][0])  # Preț de închidere
    except Exception as e:
        logging.error(f"Eroare la get_price: {e}")
        return 0.0

# Returnează balanța BTC sau EUR
def get_balance(asset='XXBT'):
    try:
        balance = api.query_private('Balance')['result']
        return float(balance.get(asset, 0.0))
    except Exception as e:
        logging.error(f"Eroare la get_balance: {e}")
        return 0.0

# Plasează un ordin market (buy/sell)
def place_market_order(pair='XBTEUR', side='buy', volume=0.0001):
    try:
        response = api.query_private('AddOrder', {
            'pair': pair,
            'type': side,
            'ordertype': 'market',
            'volume': volume,
        })

        if response.get('error'):
            logging.info(f"❌ Eroare la plasarea ordinului: {response['error']}")
        else:
            logging.info(f"✅ Ordin {side.upper()} plasat: {volume} BTC")

        return response
    except Exception as e:
        logging.error(f"❌ Eroare la execuția ordinului: {e}")
        return None

# Testare locală
if __name__ == "__main__":
    btc_balance = get_balance('XXBT')
    eur_balance = get_balance('ZEUR')
    price = get_price()

    print(f"BTC balance: {btc_balance}")
    print(f"EUR balance: {eur_balance}")
    print(f"Preț curent BTC/EUR: {price}")
