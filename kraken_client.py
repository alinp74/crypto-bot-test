import os
from dotenv import load_dotenv
import krakenex

# Încarcă .env
load_dotenv()

API_KEY = os.getenv("KRAKEN_API_KEY")
API_SECRET = os.getenv("KRAKEN_API_SECRET")

# Verificăm dacă sunt încărcate corect
if not API_KEY or not API_SECRET:
    raise Exception("❌ Cheile API nu sunt încărcate! Verifică fișierul .env.")

k = krakenex.API()
k.key = API_KEY
k.secret = API_SECRET

def check_kraken_connection():
    try:
        response = k.query_private('Balance')
        if 'error' in response and response['error']:
            print("❌ Eroare:", response['error'])
        else:
            print("✅ Conectare reușită!")
            for coin, amount in response['result'].items():
                print(f"{coin}: {amount}")
    except Exception as e:
        print("❌ Eroare conexiune:", str(e))

if __name__ == "__main__":
    check_kraken_connection()
