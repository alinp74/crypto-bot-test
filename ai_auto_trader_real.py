import json
import time
import logging
from datetime import datetime
import krakenex
import pandas as pd
from pykrakenapi import KrakenAPI
from ai_risk_manager import manage_risk
from log_trade import log_trade

# Setări log
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

# Încarcă strategia optimă
try:
    with open("strategy.json", "r") as file:
        best_strategy = json.load(file)
        logging.info(f"✅ Strategie încărcată: {best_strategy}")
except FileNotFoundError:
    logging.error("❌ Strategie optimă nu a fost găsită.")
    best_strategy = {}

# Config API Kraken
api = krakenex.API()
api.load_key('kraken.key')  # Asigură-te că acest fișier există și are cheia în formatul corect
k = KrakenAPI(api)

# Funcții indicatori
def calculate_rsi(data, period):
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_macd(data, fast, slow, signal):
    ema_fast = data.ewm(span=fast, adjust=False).mean()
    ema_slow = data.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    return macd_line, signal_line

# Execută tranzacție
def execute_trade(pair, action, volume):
    try:
        response = api.query_private('AddOrder', {
            'pair': pair,
            'type': action,
            'ordertype': 'market',
            'volume': volume
        })
        logging.info(f"✅ Tranzacție {action.upper()} executată: {response}")
        log_trade(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), pair, action, volume, best_strategy)
    except Exception as e:
        logging.error(f"❌ Eroare la execuția tranzacției: {e}")

# Rulează botul
def run_bot():
    pair = 'XBTUSDT'
    interval = 5

    while True:
        try:
            # Date de piață
            ohlc, _ = k.get_ohlc_data(pair, interval=interval)
            df = ohlc[['close']].copy()
            df['close'] = pd.to_numeric(df['close'])

            if len(df) < best_strategy['RSI_Period']:
                logging.warning("📉 Nu sunt suficiente date pentru calcul RSI.")
                time.sleep(60)
                continue

            # Indicatori
            df['RSI'] = calculate_rsi(df['close'], best_strategy['RSI_Period'])
            df['MACD'], df['Signal'] = calculate_macd(df['close'],
                                                      best_strategy['MACD_Fast'],
                                                      best_strategy['MACD_Slow'],
                                                      best_strategy['MACD_Signal'])

            latest_rsi = df['RSI'].iloc[-1]
            latest_macd = df['MACD'].iloc[-1]
            latest_signal = df['Signal'].iloc[-1]

            # Evaluare risc
            risk = manage_risk(df['close'])  # ✅ FIX: Acum trimite doar seria de prețuri
            risk_score = risk['risk_score']
            volatility = risk['volatility']
            position_size = risk['position_size']

            logging.info(f"📊 RiskScore={risk_score:.2f} | Volatilitate={volatility:.4f} | DimPoz={position_size:.5f} BTC")

            # Semnal tranzacționare
            action = None
            if latest_rsi < best_strategy['RSI_OS'] and latest_macd > latest_signal:
                action = 'buy'
            elif latest_rsi > best_strategy['RSI_OB'] and latest_macd < latest_signal:
                action = 'sell'

            if action:
                execute_trade(pair, action, position_size)
            else:
                logging.info(f"⏳ Fără semnal clar. Ultimul preț: {df['close'].iloc[-1]}")

        except Exception as e:
            logging.error(f"❌ Eroare în run_bot: {e}")

        time.sleep(60)

if best_strategy:
    logging.info(f"🤖 Bot AI REAL pornit! Strategia optimă: {best_strategy}")
    run_bot()
else:
    logging.error("⚠️ Botul nu poate porni fără strategie.")
