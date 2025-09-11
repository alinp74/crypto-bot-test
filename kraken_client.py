import os
import krakenex
from dotenv import load_dotenv

# Încarcă variabilele din fișierul .env
load_dotenv()

# Creează instanța clientului Kraken
api = krakenex.API()

# Setează cheile din variabilele de mediu (.env)
api.key = os.getenv("KRAKEN_API_KEY")
api.secret = os.getenv("KRAKEN_API_SECRET")

# Funcție pentru a obține balanța pentru un simbol (de ex: 'XXBT' pentru BTC)
def get_balance(symbol='XXBT'):
    try:
        response = api.query_private('Balance')
        return float(response['result'].get(symbol, 0.0))
    except Exception as e:
        print(f"Eroare la get_balance: {e}")
        return 0.0

# Funcție pentru a obține prețul curent BTC/EUR
def get_price(pair='XBTEUR'):
    try:
        ticker = api.query_public('Ticker', {'pair': pair})
        result = ticker['result']
        key = list(result.keys())[0]  # Extrage cheia reală (ex: 'XXBTZEUR')
        return float(result[key]['c'][0])
    except Exception as e:
        print(f"Eroare la get_price: {e}")
        return 0.0


# Funcție pentru a plasa un ordin de tip market
def place_market_order(pair='XBTEUR', side='buy', volume=0.0001):
    try:
        response = api.query_private('AddOrder', {
            'pair': pair,
            'type': side.lower(),         # ✅ asigură-te că este lowercase
            'ordertype': 'market',
            'volume': str(volume)         # ✅ Kraken cere string
        })
        print(f"✅ Ordin {side.upper()} plasat: {volume} BTC")
        return response
    except Exception as e:
        print(f"❌ Eroare la plasarea ordinului: {e}")
        return Nonedef place_market_order(pair='XBTEUR', side='buy', volume=0.0001):
    try:
        # Kraken necesită volume sub formă de șir (string)
        volume_str = str(volume)

        response = api.query_private('AddOrder', {
            'pair': pair,
            'type': side,
            'ordertype': 'market',
            'volume': volume_str
        })

        # 🔍 Log complet de debug
        logging.debug(f"🔎 Răspuns Kraken AddOrder: {response}")

        # Dacă există erori, nu continuăm
        if response.get('error'):
            logging.error(f"❌ Eroare la plasarea ordinului: {response['error']}")
            return False

        # Succes: ordin plasat
        logging.info(f"✅ Ordin {side.upper()} plasat: {volume_str} BTC")
        return True

    except Exception as e:
        logging.error(f"❌ Excepție la plasarea ordinului: {str(e)}")
        return False



# Testare directă (doar dacă rulezi acest fișier direct)
if __name__ == "__main__":
    print("✅ Conectare reușită.")
    btc_balance = get_balance('XXBT')
    print(f"BTC balance: {btc_balance}")
    price = get_price()
    print(f"Preț curent BTC/EUR: {price}")
