import os
import krakenex

# Inițializează clientul Kraken
api = krakenex.API()

# Încarcă cheile din variabile de mediu
api_key = os.getenv("KRAKEN_API_KEY")
api_secret = os.getenv("KRAKEN_API_SECRET")

if not api_key or not api_secret:
    raise ValueError("❌ Cheile KRAKEN_API_KEY sau KRAKEN_API_SECRET lipsesc din environment!")

api.key = api_key
api.secret = api_secret


def get_price(pair='XXBTZEUR'):
    """Returnează ultimul preț pentru o pereche dată."""
    try:
        response = api.query_public('Ticker', {'pair': pair})
        result = response['result']
        price = list(result.values())[0]['c'][0]
        return float(price)
    except Exception as e:
        print(f"[get_price] ❌ Eroare: {e}")
        return None


def get_balance():
    """Returnează balanța curentă a contului."""
    try:
        response = api.query_private('Balance')
        if 'result' in response:
            return response['result']
        else:
            print(f"[get_balance] ❌ Eroare: {response.get('error')}")
            return {}
    except Exception as e:
        print(f"[get_balance] ❌ Eroare: {e}")
        return {}


def place_market_order(pair='XXBTZEUR', type='buy', volume='0.001'):
    """Plasează un ordin de tip market."""
    try:
        response = api.query_private('AddOrder', {
            'pair': pair,
            'type': type,
            'ordertype': 'market',
            'volume': volume
        })
        if 'result' in response:
            return response['result']
        else:
            print(f"[place_market_order] ❌ Eroare: {response.get('error')}")
            return {}
    except Exception as e:
        print(f"[place_market_order] ❌ Eroare: {e}")
        return {}
