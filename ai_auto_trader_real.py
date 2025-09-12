import time
import json
import logging
import requests
import pandas as pd
from ai_risk_manager import manage_risk
from log_trade import log_trade

KRAKEN_API_URL = 'https://api.kraken.com/0/public/OHLC?pair=XXBTZUSD&interval=1'

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

def load_strategy():
    try:
        with open("strategy.json", "r") as file:
            strategy = json.load(file)
            logging.info(f"✅ Strategie încărcată: {strategy}")
            return strategy
    except FileNotFoundError:
        logging.error("❌ Strategie optimă nu a fost găsită.")
        return None

def fetch_price_data():
    try:
        response = requests.get(KRAKEN_API_URL)
        data = response.json()
        ohlc_data = data['result']['XXBTZUSD']
        df = pd.DataFrame(ohlc_data, columns=[
            'time', 'open', 'high', 'low', 'close', 'vwap', 'volume', 'count'
        ])
        df['close'] = df['close'].astype(float)
        return df
    except Exception as e:
        logging.error(f"❌ Eroare la preluarea datelor: {e}")
        return None

def calculate_indicators(df, strategy):
    try:
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(strategy['RSI_Period']).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(strategy['RSI_Period']).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        # MACD
        exp1 = df['close'].ewm(span=strategy['MACD_Fast'], adjust=False).mean()
        exp2 = df['close'].ewm(span=strategy['MACD_Slow'], adjust=False).mean()
        macd = exp1 - exp2
        signal = macd.ewm(span=strategy['MACD_Signal'], adjust=False).mean()

        return rsi, macd, signal
    except Exception as e:
        logging.error(f"❌ Eroare la calcularea indicatorilor: {e}")
        return None, None, None

def decide_trade(rsi, macd, signal, strategy):
    if rsi is None or macd is None or signal is None:
        return "HOLD"

    if rsi.iloc[-1] < strategy['RSI_OS'] and macd.iloc[-1] > signal.iloc[-1]:
        return "BUY"
    elif rsi.iloc[-1] > strategy['RSI_OB'] and macd.iloc[-1] < signal.iloc[-1]:
        return "SELL"
    else:
        return "HOLD"

def execute_trade(signal, price, risk):
    logging.info(f"📈 Semnal: {signal} | Preț: {price} | RiskScore={risk['risk_score']} | Volatilitate={risk['volatility']} | Poz={risk['position_size']} BTC")
    log_trade(signal, price, risk['risk_score'], risk['volatility'], risk['position_size'])

def run_bot():
    strategy = load_strategy()
    if not strategy:
        return

    logging.info(f"🤖 Bot AI REAL pornit! Strategia optimă: {strategy}")

    while True:
        df = fetch_price_data()
        if df is not None:
            rsi, macd, signal = calculate_indicators(df, strategy)
            trade_signal = decide_trade(rsi, macd, signal, strategy)

            risk = manage_risk(df['close'].values)
            execute_trade(trade_signal, df['close'].iloc[-1], risk)
        else:
            logging.warning("⚠️ Nu s-au putut prelua datele.")

        time.sleep(60)

if __name__ == "__main__":
    run_bot()
