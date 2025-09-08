import pandas as pd
import numpy as np
from binance.client import Client
from dotenv import load_dotenv
import os
import json

load_dotenv()
API_KEY = os.getenv("API_KEY_MAINNET")
API_SECRET = os.getenv("API_SECRET_MAINNET")
client = Client(API_KEY, API_SECRET)

SYMBOL = "BTCUSDT"
CAPITAL_TOTAL = 10000
RISK_PER_TRADE = 0.01  # 1% din capital per tranzacție
MAX_DAILY_DRAWDOWN = 0.1  # Botul se oprește dacă pierde 10% într-o zi

# === DESCĂRCARE DATE ===
def get_historical_data(interval="15m", limit=100):
    klines = client.get_klines(symbol=SYMBOL, interval=interval, limit=limit)
    df = pd.DataFrame(klines, columns=[
        "timestamp","open","high","low","close","volume",
        "close_time","qav","num_trades","tbbav","tbqav","ignore"
    ])
    df["close"] = df["close"].astype(float)
    df["high"] = df["high"].astype(float)
    df["low"] = df["low"].astype(float)
    return df

# === CALCUL VOLATILITATE ===
def calculate_volatility(df):
    df["returns"] = df["close"].pct_change()
    volatility = df["returns"].std() * np.sqrt(len(df))
    return volatility

# === DIMENSIUNE POZIȚIE ===
def calculate_position_size(capital, stop_loss_pct, volatility):
    # Dacă volatilitatea e mare, reducem dimensiunea poziției
    adj_risk = RISK_PER_TRADE / (volatility if volatility > 0.01 else 1)
    position_size = capital * adj_risk / (stop_loss_pct / 100)
    return round(position_size, 5)

# === STOP-LOSS DINAMIC ===
def dynamic_stop_loss(volatility):
    if volatility < 0.02:
        return 3.0   # piață stabilă → riscăm mai mult
    elif volatility < 0.05:
        return 2.0
    else:
        return 1.0   # piață foarte volatilă → risc minim

# === VERIFICĂ DRAWDOWN ===
def check_daily_drawdown():
    if os.path.exists("trade_log.json"):
        with open("trade_log.json", "r") as f:
            trades = json.load(f)
        today = pd.Timestamp.now().strftime("%Y-%m-%d")
        pnl_today = sum([t.get("pnl", 0) for t in trades if t["time"].startswith(today)])
        if pnl_today <= -CAPITAL_TOTAL * MAX_DAILY_DRAWDOWN:
            return False  # Botul trebuie oprit
    return True

# === RISK SCORE AI ===
def risk_score(volatility, strategy_confidence):
    """Scor între 0 și 1; dacă e sub 0.5 → botul evită tranzacția"""
    vol_factor = 1 - min(volatility * 10, 1)   # volatilitate mare = risc mai mare
    score = (vol_factor + strategy_confidence) / 2
    return round(score, 2)

# === APLICARE LOGICĂ RISC ===
def manage_risk():
    df = get_historical_data()
    volatility = calculate_volatility(df)
    stop_loss_pct = dynamic_stop_loss(volatility)
    position_size = calculate_position_size(CAPITAL_TOTAL, stop_loss_pct, volatility)

    # Simulăm că strategia are încredere 70%
    strategy_confidence = 0.7
    score = risk_score(volatility, strategy_confidence)

    return {
        "Volatilitate": round(volatility, 4),
        "StopLoss%": stop_loss_pct,
        "DimensiunePozitieBTC": position_size,
        "RiskScore": score,
        "Tranzactioneaza": score >= 0.5 and check_daily_drawdown()
    }

if __name__ == "__main__":
    risk_data = manage_risk()
    print("\n===== AI RISK MANAGER =====")
    for k, v in risk_data.items():
        print(f"{k}: {v}")
