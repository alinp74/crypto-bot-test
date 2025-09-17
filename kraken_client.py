import krakenex
from pykrakenapi import KrakenAPI
import os
import time

api = krakenex.API()
api.load_key('.env') if os.path.exists('.env') else None
k = KrakenAPI(api)

def get_price(pair="XXBTZEUR"):
    try:
        data = k.get_ticker_information(pair)
        return float(data['c'][0][0])
    except Exception as e:
        print(f"[get_price] Eroare: {e}")
        return None

def get_ohlc(pair="XXBTZEUR", interval=5, lookback=100):
    """Preia date OHLC pentru strategie"""
    try:
        df, _ = k.get_ohlc_data(pair, interval=interval)
        return df.tail(lookback)
    except Exception as e:
        print(f"[get_ohlc] Eroare: {e}")
        return None
