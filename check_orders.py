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
# Setăm simbolul monedei tranzacționate
symbol = "BTCUSDT"

# Obținem toate ordinele pentru simbolul respectiv
orders = client.get_all_orders(symbol=symbol)

print("=== ORDINE ACTIVE / FINALIZATE ===")
for order in orders:
    print(f"ID: {order['orderId']} | Tip: {order['side']} | Cantitate: {order['origQty']} | Preț: {order['price']} | Status: {order['status']}")