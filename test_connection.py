import os
from dotenv import load_dotenv
from binance.client import Client

load_dotenv()
API_KEY = os.getenv("API_KEY_MAINNET")
API_SECRET = os.getenv("API_SECRET_MAINNET")

client = Client(API_KEY, API_SECRET)

try:
    account = client.get_account()
    balances = account["balances"]
    usdt = [b for b in balances if b["asset"] == "USDT"][0]
    btc = [b for b in balances if b["asset"] == "BTC"][0]
    print(f"✅ Conexiune reușită! Sold curent: {btc['free']} BTC | {usdt['free']} USDT")
except Exception as e:
    print(f"❌ Eroare conectare: {e}")
