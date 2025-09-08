import os
from dotenv import load_dotenv
from binance.client import Client

# Încărcăm cheile API din .env
load_dotenv()
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")

# Conectare la Binance Testnet
client = Client(API_KEY, API_SECRET)
client.API_URL = "https://testnet.binance.vision/api"

# Obținem informații despre cont
account = client.get_account()
print("=== WALLET TESTNET ===")
for balance in account["balances"]:
    free = float(balance["free"])
    locked = float(balance["locked"])
    if free > 0 or locked > 0:
        print(f"{balance['asset']}: liber = {free}, blocat = {locked}")