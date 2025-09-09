import os
import json
import time
from datetime import datetime

import pandas as pd
import ta
from dotenv import load_dotenv

from binance.client import Client
from binance.enums import *

from ai_risk_manager import manage_risk   # Asigură-te că acest fișier există
from log_trade import log_decizie         # Asigură-te că acest fișier există

# === CONFIG ===
load_dotenv()

API_KEY = os.getenv("API_KEY_MAINNET")
API_SECRET = os.getenv("API_SECRET_MAINNET")
SYMBOL = "BTCUSDT"

client = Client(API_KEY, API_SECRET)

# === Logare decizie și mesaje ===
def log_trade(message):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_msg = f"[{timestamp}] {message}"
    print(log_msg)
    try:
        with open("log_trade.txt", "a") as f:
            f.write(log_msg + "\n")
    except Exception as e:
        print(f"[Eroare log_trade.txt] {e}")

# === Încărcare strategie optimă din fișier ===
def load_strategy():
    if os.path.exists("strategie_optima.json"):
        with open("strategie_optima.json", "r") as f:
            return json.load(f)
    return None

# === Preluare istoric prețuri ===
def get_price_data():
    try:
        klines = client.get_klines(symbol=SYMBOL, interval=Client.KLINE_INTERVAL_1MINUTE, limit=100)
        df = pd.DataFrame(klines, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_asset_volume', 'number_of_trades',
            'taker_buy_base_volume', 'taker_buy_quote_volume', 'ignore'
        ])
        df['close'] = pd.to_numeric(df['close'])
        return df
    except Exception as e:
        log_trade(f"Eroare la preluarea datelor de preț: {e}")
        return None

# === Calcul semnal strategie ===
def signal_strategy(df, strat):
    try:
        df['rsi'] = ta.momentum.RSIIndicator(df['close'], strat['RSI_Period']).rsi()
        macd = ta.trend.MACD(df['close'], strat['MACD_Fast'], strat['MACD_Slow'], strat['MACD_Signal'])
        df['macd'] = macd.macd()
        df['macd_signal'] = macd.macd_signal()

        latest = df.iloc[-1]
        if latest['rsi'] < strat['RSI_OS'] and latest['macd'] > latest['macd_signal']:
            return "BUY"
        elif latest['rsi'] > strat['RSI_OB'] and latest['macd'] < latest['macd_signal']:
            return "SELL"
        else:
            return "HOLD"
    except Exception as e:
        log_trade(f"Eroare la calcul semnal: {e}")
        return "HOLD"

# === Executare tranzacție ===
def place_order(side, quantity):
    try:
        order = client.create_order(
            symbol=SYMBOL,
            side=side,
            type=ORDER_TYPE_MARKET,
            quantity=quantity
        )
        log_trade(f"Executat {side} - Cantitate: {quantity}")
    except Exception as e:
        log_trade(f"Eroare plasare ordin {side}: {e}")

# === Bot AI principal ===
def run_bot():
    strategy = load_strategy()
    if not strategy:
        log_trade("❌ Strategie optimă nu a fost găsită.")
        return

    log_trade(f"🤖 Bot AI REAL pornit! Strategia optimă: {strategy}")
    while True:
        df = get_price_data()
        if df is None:
            time.sleep(60)
            continue

        signal = signal_strategy(df, strategy)
        last_price = df['close'].iloc[-1]

        risk = manage_risk(df['close'])
        log_trade(f"📊 RiskScore={risk['score']:.2f} | Volatilitate={risk['volatility']:.4f} | DimPoz={risk['position_size']:.5f} BTC")

        if signal in ["BUY", "SELL"]:
            log_decizie(signal, last_price, strategy, risk['score'])
            place_order(SIDE_BUY if signal == "BUY" else SIDE_SELL, round(risk['position_size'], 5))
        else:
            log_trade(f"⏳ Fără semnal clar. Ultimul preț: {last_price}")
        time.sleep(60)

if __name__ == "__main__":
    run_bot()
