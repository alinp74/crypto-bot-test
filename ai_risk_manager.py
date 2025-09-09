import numpy as np
import pandas as pd

def manage_risk(close_prices):
    if close_prices.empty:
        return {
            "risk_score": 0.0,
            "volatility": 0.0,
            "position_size": 0.0
        }

    volatility = close_prices.pct_change().std()
    risk_score = min(volatility * 100, 1.0)

    # Ex: determină poziția în funcție de risc
    position_size = round(1000 / close_prices.iloc[-1], 5)  # ~1000 USDT

    return {
        "risk_score": risk_score,
        "volatility": volatility,
        "position_size": position_size
    }
