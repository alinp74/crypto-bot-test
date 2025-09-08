import os
from dotenv import load_dotenv
from binance.client import Client

load_dotenv()
API_KEY = os.getenv("API_KEY_MAINNET")
API_SECRET = os.getenv("API_SECRET_MAINNET")

client = Client(API_KEY, API_SECRET)

try:
    account_info = client.get_account()
    print("✅ API-ul funcționează!")
    print("Permisiuni pentru Spot Trading confirmate.")
except Exception as e:
    print(f"❌ Eroare: {e}")
