import krakenex
from pykrakenapi import KrakenAPI
import pandas as pd
import warnings
import logging

# Configurare logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# Ignoră warningurile cu 'T' deprecated și alte FutureWarnings
warnings.filterwarnings("ignore", category=FutureWarning, module="pykrakenapi")

# Conexiune Kraken
api = krakenex.API()
k = KrakenAPI(api)


def get_price(pair: str):
    """
    Returnează ultimul preț pentru un pair de pe Kraken.
    """
    try:
        data = api.query_public("Ticker", {"pair": pair})
        if "error" in data and data["error"]:
            logger.error(f"[get_price] Eroare Kraken: {data['error']}")
            return None
        return float(data["result"][pair]["c"][0])
    except Exception as e:
        logger.error(f"[get_price] Eroare: {e}")
        return None


def get_ohlc(pair: str, interval=1, since=None):
    """
    Returnează date OHLC ca DataFrame Pandas.
    """
    try:
        ohlc, last = k.get_ohlc_data(pair, interval=interval, since=since)
        return ohlc
    except Exception as e:
        logger.error(f"[get_ohlc] Eroare: {e}")
        return pd.DataFrame()
