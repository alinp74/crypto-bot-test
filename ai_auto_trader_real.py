import logging
from datetime import datetime
from kraken_client import get_price, get_balance, place_market_order
import time
import json

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s')
logger = logging.getLogger(__name__)

STRATEGY_FILE = "strategii.json"

def load_strategy():
    try:
        with open(STRATEGY_FILE, "r") as f:
            strategy = json.load(f)
        logger.info(f"✅ Strategie încărcată: {strategy}")
        return strategy
    except Exception as e:
        logger.error(f"❌ Eroare la încărcarea strategiei: {e}")
        default_strategy = {
            'RSI_Period': 7,
            'RSI_OB': 50,
            'RSI_OS': 50,
            'MACD_Fast': 8,
            'MACD_Slow': 26,
            'MACD_Signal': 9,
            'Stop_Loss': 1,
            'Take_Profit': 2.0,
            'Profit': 0,
            'Updated': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        with open(STRATEGY_FILE, "w") as f:
            json.dump(default_strategy, f, indent=4)
        return default_strategy

def analyze_market(strategy, price):
    # TODO: Înlocuiește cu calcule reale RSI, MACD, etc.
    signal = "HOLD"
    risk_score = 0.0
    volatility = 0.0
    return signal, risk_score, volatility

def main():
    strategy = load_strategy()
    logger.info(f"🤖 Bot AI REAL pornit! Strategia optimă: {strategy}")

    while True:
        try:
            price = get_price()
            signal, risk_score, volatility = analyze_market(strategy, price)
            balance = get_balance()

            logger.info(f"📈 Semnal: {signal} | Preț: {price} | RiskScore={risk_score:.2f} | Volatilitate={volatility:.4f} | Poz={balance} BTC")

            if signal == "BUY":
                place_market_order("buy", 0.001)
            elif signal == "SELL":
                place_market_order("sell", 0.001)

            time.sleep(10)

        except Exception as e:
            logger.error(f"❌ Eroare în rulare: {e}")
            time.sleep(10)

if __name__ == "__main__":
    main()
