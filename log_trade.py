from datetime import datetime

def log_decizie(signal, price, risk, strategy):
    mesaj = f"""[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] 
    Acțiune: {signal} | Preț: {price} USDT
    RSI: {strategy['RSI_Period']} ({strategy['RSI_OS']}/{strategy['RSI_OB']})
    MACD: Fast={strategy['MACD_Fast']}, Slow={strategy['MACD_Slow']}, Signal={strategy['MACD_Signal']}
    Risc: Scor={risk['RiskScore']}, Volatilitate={risk['Volatilitate']}, Poz={risk['DimensiunePozitieBTC']} BTC
    """

    with open("log_trade.txt", "a") as f:
        f.write(mesaj + "\n")
