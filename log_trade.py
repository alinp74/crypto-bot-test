from datetime import datetime

def log_trade(signal, price, risk_score, volatility, position_size):
    with open("log_trade.txt", "a") as f:
        f.write(f"{datetime.now()} | Semnal: {signal} | Preț: {price} | Risk: {risk_score} | Vol: {volatility} | Poz: {position_size} BTC\n")
