import os
import krakenex

# Inițializare client Kraken
k = krakenex.API()
k.key = os.environ.get("KRAKEN_API_KEY")
k.secret = os.environ.get("KRAKEN_API_SECRET")

if not k.key or not k.secret:
    raise ValueError("❌ Cheile KRAKEN_API_KEY sau KRAKEN_API_SECRET lipsesc din environment!")

def get_price(pair='XXBTZEUR'):
    try:
        response = k.query_public('Ticker', {'pair': pair})
        if response.get("error"):
            print(f"[get_price] Eroare: {response['error']}")
            return None
        return float(response['result'][list(response['result'].keys())[0]]['c'][0])
    except Exception as e:
        print(f"[get_price] Eroare: {e}")
        return None

def get_balance():
    try:
        response = k.query_private('Balance')
        if response.get("error"):
            print(f"[get_balance] Eroare: {response['error']}")
            return None
        return response['result']
    except Exception as e:
        print(f"[get_balance] Eroare: {e}")
        return None

def place_market_order(pair, type_, volume):
    try:
        order = {
            'pair': pair,
            'type': type_,
            'ordertype': 'market',
            'volume': volume
        }
        response = k.query_private('AddOrder', order)
        if response.get("error"):
            print(f"[place_market_order] Eroare: {response['error']}")
            return None
        return response['result']
    except Exception as e:
        print(f"[place_market_order] Eroare: {e}")
        return None
