import krakenex
from datetime import datetime

# Inițializare API
api = krakenex.API()
api.load_key('kraken.key')  # Asigură-te că ai un fișier `kraken.key` cu cheia ta API

# Obține prețul actual BTC/EUR
def get_price(pair='XBTEUR'):
    try:
        result = api.query_public('Ticker', {'pair': pair})
        ticker = list(result['result'].values())[0]  # Luați primul rezultat din dict
        return float(ticker['c'][0])  # Prețul de închidere (ultimul preț)
    except Exception as e:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Eroare la get_price: {e}")
        return 0.0

# Obține balanța pentru un anumit asset
def get_balance(asset='XXBT'):
    try:
        response = api.query_private('Balance')
        return float(response['result'].get(asset, 0.0))
    except Exception as e:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Eroare la get_balance: {e}")
        return 0.0

# Plasează un ordin de tip market
def place_market_order(pair='XBTEUR', side='buy', volume=0.0001):
    try:
        response = api.query_private('AddOrder', {
            'pair': pair,
            'type': side,
            'ordertype': 'market',
            'volume': str(volume),  # Kraken cere volumele ca string
        })

        if response.get('error'):
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ❌ Eroare la plasarea ordinului: {response['error']}")
        else:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ✅ Ordin {side.upper()} plasat: {volume} BTC")

    except Exception as e:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Eroare la place_market_order: {e}")
