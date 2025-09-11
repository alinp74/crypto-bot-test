import time
import json
import logging
import pandas as pd
from datetime import datetime
from ai_risk_manager import manage_risk
from log_trade import log_trade_decision
from kraken_client import get_price, get_balance, place_market_order
from technical_indicators import calculate_indicators

# Configurare log
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s')

def load_strategy():
    try:
        with open("strategy.json", "r") as f:
            strategy = json.load(f)
        logging.info(f"✅ Strategie încărcată: {strategy}")
        return strategy
    except Exception as e:
        logging.error("❌ Strategie optimă nu a fost găsită.")
        return None

def calculate_position_size(risk_score, balance_eur, current_price):
    if current_price == 0:
        return 0
    position_eur = balance_eur * risk_score
    position_btc = position_eur / current_price
    return round(position_btc, 8)

def evaluate_market_signal(df, strategy):
    rsi = df['rsi'].iloc[-1]
    macd = df['macd'].iloc[-1]
    signal = df['signal'].iloc[-1]

    if rsi < strategy["RSI_OS"] and macd > signal:
        return "BUY"
    elif rsi > strategy["RSI_OB"] and macd < signal:
        return "SELL"
    else:
        return "HOLD"

def run_bot():
    strategy = load_strategy()
    if not strategy:
        return

    logging.info(f"🤖 Bot AI REAL pornit! Strategia optimă: {strategy}")

    while True:
        try:
            # 1. Preluare date piață
            price = get_price()
            if price is None:
                logging.warning("❌ Nu s-a putut obține prețul curent.")
                time.sleep(60)
                continue

            # 2. Preluare balanțe
            balances = get_balance()
            balance_btc = balances.get('XXBT', 0)
            balance_eur = balances.get('ZEUR', 0)

            # 3. Creare DataFrame cu preț
            df = pd.DataFrame({'close': [price] * 100})  # Dummy data
            df = calculate_indicators(df)

            # 4. Calcul risk și dimensiune poziție
            risk = manage_risk(df['close'])
            volatility = df['close'].pct_change().rolling(10).std().iloc[-1]
            position_size = calculate_position_size(risk, balance_eur, price)

            # 5. Evaluare semnal
            signal = evaluate_market_signal(df, strategy)

            logging.info(f"📈 Semnal: {signal} | Preț: {price} | RiskScore={round(risk, 2)} | Volatilitate={round(volatility, 4)} | Poz={position_size} BTC")
            log_trade_decision(signal, price, position_size, risk)

            # 6. Executare ordin
            if signal == "BUY" and balance_eur > 5:
                response = place_market_order("buy", "XXBTZEUR", position_size)
                logging.info(f"✅ Ordin BUY plasat: {response}")
            elif signal == "SELL" and balance_btc > 0.00001:
                response = place_market_order("sell", "XXBTZEUR", balance_btc)
                logging.info(f"✅ Ordin SELL plasat: {response}")

        except Exception as e:
            logging.error(f"❌ Eroare în rulare: {str(e)}")

        time.sleep(60)  # Așteaptă 1 minut

if __name__ == "__main__":
    run_bot()
