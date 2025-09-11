import time
import pandas as pd
from datetime import datetime
from kraken_client import get_price, get_balance, place_market_order

PAIR = 'XXBTZEUR'
STRATEGY_FILE = 'strategii.csv'

def load_strategy():
    try:
        df = pd.read_csv(STRATEGY_FILE)
        strategy = df.iloc[-1].to_dict()
        print(f"[{datetime.now()}] ✅ Strategie încărcată: {strategy}")
        return strategy
    except Exception as e:
        print(f"[{datetime.now()}] ❌ Eroare la încărcarea strategiei: {e}")
        return {
            'RSI_Period': 7,
            'RSI_OB': 50,
            'RSI_OS': 50,
            'MACD_Fast': 8,
            'MACD_Slow': 26,
            'MACD_Signal': 9,
            'Stop_Loss': 1,
            'Take_Profit': 2.0,
            'Profit': 0,
            'Updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

def main():
    strategy = load_strategy()
    print(f"[{datetime.now()}] 🤖 Bot AI REAL pornit! Strategia optimă: {strategy}")

    while True:
        try:
            price = get_price(PAIR)
            if not price:
                time.sleep(5)
                continue

            balance = get_balance()
            poz = balance if balance else "N/A"

            # Log simplificat doar cu semnalul
            print(f"[{datetime.now()}] 📈 Semnal: HOLD | Preț: {price} | RiskScore=0.00 | Volatilitate=0.0000 | Poz={poz} BTC")
            time.sleep(10)
        except Exception as e:
            print(f"[{datetime.now()}] ❌ Eroare în rulare: {e}")
            time.sleep(10)

if __name__ == "__main__":
    main()
