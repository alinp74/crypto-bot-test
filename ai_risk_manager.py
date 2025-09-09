import numpy as np
import pandas as pd

def manage_risk(close_prices):
    if close_prices.empty:
        return 0.0

    volatility = close_prices.pct_change().std()
    risk_score = min(volatility * 100, 1.0)  # scalat la [0.0, 1.0]
    return risk_score

    
