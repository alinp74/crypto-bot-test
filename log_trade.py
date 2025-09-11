from datetime import datetime

def log_trade_decision(signal, price, position_size, risk_score):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = (
        f"[{timestamp}] Semnal: {signal} | Preț: {price} | "
        f"Poz={position_size} BTC | RiskScore={round(risk_score, 2)}\n"
    )
    
    try:
        with open("log_trade.txt", "a") as f:
            f.write(log_entry)
    except Exception as e:
        print(f"Eroare la scrierea în fișierul de log: {e}")
