import time
import datetime
import logging
import pandas as pd
from kraken_client import get_price, get_balance, place_market_order

# Configurare logging (doar semnale importante)
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Extragere strategii dintr-un fișier CSV
def incarca_strategie_din_csv():
    try:
        df = pd.read_csv("strategii.csv")
        strategie_optima = df.loc[df['Profit'].idxmax()].to_dict()
        logging.info(f"✅ Strategie încărcată: {strategie_optima}")
        return strategie_optima
    except Exception as e:
        logging.error(f"❌ Eroare la încărcarea strategiei: {e}")
        return None

# Simulare semnal de tranzacționare
def calculeaza_semnal():
    # Placeholder pentru logică reală
    return "HOLD"

# Rulare principală a botului
def ruleaza_bot():
    strategie = incarca_strategie_din_csv()
    if not strategie:
        return

    logging.info(f"🤖 Bot AI REAL pornit! Strategia optimă: {strategie}")

    while True:
        try:
            pret = get_price()
            semnal = calculeaza_semnal()
            balans = get_balance()
            pozitie = balans  # Poți ajusta ce vrei să afișezi

            logging.info(f"📈 Semnal: {semnal} | Preț: {pret} | Poz={pozitie}")
        except Exception as e:
            logging.error(f"❌ Eroare în rulare: {e}")

        time.sleep(10)  # Interval între iterații

# Punct de pornire
if __name__ == "__main__":
    ruleaza_bot()
import time
import json
import logging
import pandas as pd
from datetime import datetime
from technical_indicators import calculate_indicators
from ai_risk_manager import manage_risk
from kraken_client import get_price, get_balance, place_market_order
from log_trade import log_trade_decision

# Configurare log
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

SYMBOL = "XXBTZEUR"  # BTC/EUR în format Kraken
INTERVAL = 60  # secunde între iterații

# Încarcă strategia optimă
def load_strategy():
    try:
        with open("strategy.json", "r") as f:
            strategy = json.load(f)
            logging.info(f"✅ Strategie încărcată: {strategy}")
            return strategy
    except Exception as e:
        logging.error(f"❌ Eroare la încărcarea strategiei: {e}")
        return None

# Obține datele de preț din ultimele N minute
def fetch_historical_data(n=50):
    prices = []
    for _ in range(n):
        try:
            price = get_price()
            prices.append(price)
            time.sleep(1)
        except Exception as e:
            logging.warning(f"Eroare la fetch preț: {e}")
    df = pd.DataFrame(prices, columns=["close"])
    return df

# Execută logica botului
def run_bot():
    strategy = load_strategy()
    if not strategy:
        return

    logging.info(f"🤖 Bot AI REAL pornit! Strategia optimă: {strategy}")

    while True:
        try:
            df = fetch_historical_data()
            df = calculate_indicators(df, strategy)

            signal = "HOLD"
            if df["buy_signal"].iloc[-1]:
                signal = "BUY"
            elif df["sell_signal"].iloc[-1]:
                signal = "SELL"

            risk_score, volatility = manage_risk(df["close"])
            balance = get_balance("XXBT")  # BTC balance
            price = get_price()
            euro_balance = get_balance("ZEUR")

            log_trade_decision(signal, price, risk_score, volatility, balance)

            if signal == "BUY" and euro_balance > 10:
                amount = euro_balance / price
                place_market_order("buy", SYMBOL, amount)
                logging.info(f"✅ Ordin BUY plasat: {amount} BTC")
            elif signal == "SELL" and balance > 0.0001:
                place_market_order("sell", SYMBOL, balance)
                logging.info(f"✅ Ordin SELL plasat: {balance} BTC")
            else:
                logging.info(f"📈 Semnal: {signal} | Preț: {price} | RiskScore={risk_score:.2f} | Volatilitate={volatility:.4f} | Poz={balance} BTC")

            time.sleep(INTERVAL)
        except Exception as e:
            logging.error(f"❌ Eroare în rulare: {e}")
            time.sleep(INTERVAL)

if __name__ == "__main__":
    run_bot()
