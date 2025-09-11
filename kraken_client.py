import logging
import pandas as pd
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

def get_price(pair='XXBTZEUR'):
    try:
        ticker, _ = k.get_ticker_information(pair)
        close = ticker['c'].iloc[0]
        if isinstance(close, list):
            close = close[0]  # extrage primul element din listă
        return float(close)
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
