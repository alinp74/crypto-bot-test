def log_trade_decision(signal, price, risk_score, volatility, position_size):
    with open("log_trade.txt", "a") as f:
        f.write(f"{signal},{price},{risk_score:.4f},{volatility:.6f},{position_size}\n")
