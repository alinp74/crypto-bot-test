import krakenex
import os
from dotenv import load_dotenv

# Încarcă cheile API
load_dotenv()
API_KEY = os.getenv("KRAKEN_API_KEY")
API_SECRET = os.getenv("KRAKEN_API_SECRET")

# Creează client Kraken
k = krakenex.API()
k.key = API_KEY
k.secret = API_SECRET

# 🔹 1. Obține prețul curent BTC/USDT (Kraken folosește simbolul 'XBTUSDT')
def get_price():
    try:
        response = k.query_public('Ticker', {'pair': 'XBTUSDT'})
        price = response['result']['XBTUSDT']['c'][0]  # ← prețul de închidere (last trade)
        return float(price)
    except Exception as e:
        print("❌ Eroare la preluarea prețului:", str(e))
        return None






# 🔹 2. Obține soldul actual (BTC și USDT)
def get_balance():
    try:
        response = k.query_private('Balance')
        balances = response['result']
        btc = float(balances.get('XXBT', 0.0))
        usdt = float(balances.get('USDT', 0.0))
        print(f"BTC: {btc:.8f} | USDT: {usdt:.2f}")
        return btc, usdt
    except Exception as e:
        print("❌ Eroare la preluarea soldului:", str(e))
        return 0.0, 0.0

# 🔹 3. Cumpără BTC de o sumă în USDT
def buy_btc(usdt_amount):
    try:
        pair = 'XBTUSDT'
        price = get_price()
        if price is None:
            return
        volume = round(usdt_amount / price, 6)
        order = {
            'pair': pair,
            'type': 'buy',
            'ordertype': 'market',
            'volume': str(volume)
        }
        response = k.query_private('AddOrder', order)
        print("✅ Ordin de cumpărare plasat:", response)
    except Exception as e:
        print("❌ Eroare la cumpărare:", str(e))

# 🔹 4. Vinde o cantitate de BTC
def sell_btc(btc_amount):
    try:
        pair = 'XBTUSDT'
        order = {
            'pair': pair,
            'type': 'sell',
            'ordertype': 'market',
            'volume': str(btc_amount)
        }
        response = k.query_private('AddOrder', order)
        print("✅ Ordin de vânzare plasat:", response)
    except Exception as e:
        print("❌ Eroare la vânzare:", str(e))

# 🔹 5. Test rapid
if __name__ == "__main__":
    print("📈 Preț BTC/USDT:", get_price())
    get_balance()
    # buy_btc(10)     # activează doar dacă vrei să cumperi
    # sell_btc(0.001) # activează doar dacă vrei să vinzi
