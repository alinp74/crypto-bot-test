import json
import time
import logging
import pandas as pd
from datetime import datetime
from kraken_client import get_klines, get_balance, place_order
from ai_risk_manager import manage_risk
from log_trade import log_trade

# Configurare logging
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

SYMBOL = 'XBTUSDT'
INTERVAL = '15m'

def load_strategy():
    try:
        with open('strategy.json', 'r') as f:
            strategy = json.load(f)
            logging.info(f"✅ Strategie încărcată: {strategy}")
            return strategy
    except Exception as e:
        logging.error(f"❌ Strategie optimă nu a fost găsită.")
        return None

def fetch_data():
    df = get_klines(SYMBOL, INTERVAL)
    if df is not None and not df.empty:
        df['close'] = pd.to_numeric(df['close'])
    return df

def calculate_indicators(df, strategy):
    df['rsi'] = df['close'].rolling(strategy['RSI_Period']).mean()
    df['ema_fast'] = df['close'].ewm(span=strategy['MACD_Fast'], adjust=False).mean()
    df['ema_slow'] = df['close'].ewm(span=strategy['MACD_Slow'], adjust=False).mean()
    df['macd'] = df['ema_fast'] - df['ema_slow']
    df['signal'] = df['macd'].ewm(span=strategy['MACD_Signal'], adjust=False).mean()
    return df

def check_signals(df, strategy):
    latest = df.iloc[-1]
    if latest['rsi'] < strategy['RSI_OS'] and latest['macd'] > latest['signal']:
        return 'BUY'
    elif latest['rsi'] > strategy['RSI_OB'] and latest['macd'] < latest['signal']:
        return 'SELL'
    return None

def run_bot():
    strategy = load_strategy()
    if not strategy:
        return

    logging.info(f"🤖 Bot AI REAL pornit! Strategia optimă: {strategy}")

    while True:
        df = fetch_data()
        if df is None or df.empty:
            logging.warning("⚠️ Date insuficiente pentru analiză.")
            time.sleep(30)
            continue

        df = calculate_indicators(df, strategy)
        signal = check_signals(df, strategy)

        risk = manage_risk(df)  # Aici corectăm: trimitem df, nu df['close']
        logging.info(f"📊 RiskScore={risk['score']:.2f} | Volatilitate={risk['volatility']:.4f} | DimPoz={risk['position_size']:.8f} BTC")

        if signal:
            side = 'buy' if signal == 'BUY' else 'sell'
            order = place_order(side=side, volume=risk['position_size'], symbol=SYMBOL)
            if order:
                log_trade(datetime.now(), SYMBOL, side.upper(), df['close'].iloc[-1], risk['position_size'], strategy)
                logging.info(f"✅ Tranzacție {side.upper()} executată.")
            else:
                logging.warning("❌ Tranzacția nu a fost executată.")
        else:
            logging.info(f"⏳ Fără semnal clar. Ultimul preț: {df['close'].iloc[-1]:.2f}")

        time.sleep(60)

if __name__ == "__main__":
    run_bot()
