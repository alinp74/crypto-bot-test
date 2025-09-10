import numpy as np

def manage_risk(close_prices):
    if len(close_prices) < 2:
        return {
            "risk_score": 0,
            "volatility": 0,
            "position_size": 0
        }

    # Calculează volatilitatea ca deviația standard a randamentelor logaritmice
    returns = np.diff(np.log(close_prices))
    volatility = np.std(returns)

    # Score de risc simplu, între 0 și 1
    risk_score = min(1.0, max(0.01, volatility * 100))

    # Dimensiunea poziției (exemplu simplificat)
    capital = 1000  # euro
    position_size = (capital * risk_score) / close_prices[-1]

    return {
        "risk_score": round(risk_score, 2),
        "volatility": round(volatility, 4),
        "position_size": round(position_size, 5)
    }
