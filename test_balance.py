import os
from dotenv import load_dotenv
from binance.client import Client

load_dotenv()
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")

client = Client(API_KEY, API_SECRET)
client.API_URL = "https://testnet.binance.vision/api"

account = client.get_account()
for b in account["balances"]:
    if b["asset"] in ["BTC", "USDT"]:
        print(f"{b['asset']}: liber={b['free']} | blocat={b['locked']}")
