import os
import krakenex
from datetime import datetime

api = krakenex.API()
api.key = os.getenv("KRAKEN_API_KEY")
api.secret = os.getenv("KRAKEN_API_SECRET")

def get_price(pair='XBTEUR'):
    try:
        result = api.query_public('Ticker', {'pair': pair})
        ticker = list(result['result'].values())[0]
        return float(ticker['c'][0])
    except Exception as e:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Eroare la get_price: {e}")
        return 0.0

def get_balance(asset='XXBT'):
    try:
        response = api.query_private('Balance')
        return float(response['result'].get(asset, 0.0))
    except Exception as e:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Eroare la get_balance: {e}")
        return 0.0

def place_market_order(pair='XBTEUR', side='buy', volume=0.0001):
    try:
        response = api.query_private('AddOrder', {
            'pair': pair,
            'type': side,
            'ordertype': 'market',
            'volume': str(volume),
        })

        if response.get('error'):
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ❌ Eroare la plasarea ordinului: {response['error']}")
        else:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ✅ Ordin {side.upper()} plasat: {volume} BTC")
    except Exception as e:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Eroare la place_market_order: {e}")
