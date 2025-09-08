import os
from dotenv import load_dotenv
from binance.client import Client

# Încarcă API Keys din .env
load_dotenv()
API_KEY = os.getenv("API_KEY_MAINNET")
API_SECRET = os.getenv("API_SECRET_MAINNET")

# Conectare la Binance Spot Testnet
client = Client(API_KEY, API_SECRET)
client.API_URL = "https://testnet.binance.vision/api"

# Alegem explicit monedele pe care le vrem
MONED_INTERES = ["USDT", "BTC"]

try:
    account = client.get_account()
    balances = account["balances"]

    print("=== WALLET SPOT TESTNET ===")
    for balance in balances:
        asset = balance["asset"]
        if asset in MONED_INTERES:
            free = float(balance["free"])
            locked = float(balance["locked"])
            print(f"{asset}: liber={free} | blocat={locked}")

except Exception as e:
    print("❌ Eroare la conectare:", e)
