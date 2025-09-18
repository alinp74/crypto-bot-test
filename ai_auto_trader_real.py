import os
import time
import logging
import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, Prices, Signals
from strategie import semnal_tranzactionare
from kraken_client import get_price, place_market_order

# Logging
logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

# DB connection
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

Base.metadata.create_all(engine, checkfirst=True)
logging.info("✅ DB tables ready in schema public")

# Strategie hardcodată (poate fi mutată în JSON mai târziu)
strategie = {
    "symbols": ["XXBTZEUR", "ADAEUR", "XETHZEUR"],
    "allocations": {"XXBTZEUR": 0.33, "ADAEUR": 0.33, "XETHZEUR": 0.34},
    "RSI_Period": 7,
    "RSI_OB": 70,
    "RSI_OS": 30,
    "MACD_Fast": 12,
    "MACD_Slow": 26,
    "MACD_Signal": 9,
    "Stop_Loss": 3.0,
    "Take_Profit": 2.0,
    "Profit": 0,
    "Updated": datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
}
logging.info(f"✅ Strategie încărcată: {strategie}")


def log_price(session, ts, symbol, price):
    """Salvează prețul în DB"""
    try:
        entry = Prices(timestamp=ts, symbol=symbol, price=price)
        session.add(entry)
        session.commit()
        logging.info(f"✅ Preț salvat în DB: {symbol}={price}")
    except Exception as e:
        session.rollback()
        logging.error(f"[log_price] Eroare: {e}")


def log_signal(session, ts, symbol, signal):
    """Salvează semnalul în DB"""
    try:
        entry = Signals(timestamp=ts, symbol=symbol, signal=signal)
        session.add(entry)
        session.commit()
        logging.info(f"✅ Semnal salvat în DB: {symbol}={signal}")
    except Exception as e:
        session.rollback()
        logging.error(f"[log_signal] Eroare: {e}")


# Main loop
while True:
    for symbol in strategie["symbols"]:
        try:
            ts, price = get_price(symbol)
            if price is None:
                continue

            log_price(session, ts, symbol, price)

            # simulăm dataframe pentru strategie
            import pandas as pd
            df = pd.DataFrame({"close": [price] * 50})
            signal = semnal_tranzactionare(df, symbol, strategie)

            log_signal(session, ts, symbol, signal)
            logging.info(f"📈 {symbol} | Semnal={signal} | Preț={price}")

            if signal in ["BUY", "SELL"]:
                place_market_order(symbol, signal.lower(), 0.001)

        except Exception as e:
            logging.error(f"❌ Eroare în rulare {symbol}: {e}")

    time.sleep(5)
