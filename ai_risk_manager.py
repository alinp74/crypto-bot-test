import numpy as np

def manage_risk(prices):
    returns = np.log(prices / prices.shift(1)).dropna()
    volatility = returns.rolling(window=10).std().iloc[-1]
    risk_score = min(volatility * 1000, 1.0)  # Scale it
    return risk_score, volatility
