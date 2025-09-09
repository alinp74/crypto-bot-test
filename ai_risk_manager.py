import numpy as np
import pandas as pd

def manage_risk(close_prices):
    """
    Calculează scorul de risc, volatilitatea și dimensiunea poziției
    în funcție de prețurile de închidere primite ca parametru.
    """

    # Asigură-te că primim o serie de tip pandas
    if not isinstance(close_prices, pd.Series):
        close_prices = pd.Series(close_prices)

    # Calculează randamentele zilnice
    returns = close_prices.pct_change().dropna()

    # Calculează volatilitatea ca deviație standard a randamentelor
    volatility = returns.std()

    # Calculează scorul de risc invers proporțional cu volatilitatea
    risk_score = max(0.01, min(1.0, 1 - volatility * 100))  # Normalizează între 0.01 și 1.0

    # Calculează dimensiunea poziției pe baza riscului
    position_size = 100 * risk_score  # Exemplu simplificat (poate fi ajustat)

    return {
        "score": round(risk_score, 2),
        "volatility": round(volatility, 4),
        "position_size": round(position_size, 5)
    }
