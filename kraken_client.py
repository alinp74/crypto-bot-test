import krakenex
from pykrakenapi import KrakenAPI
import time

api = krakenex.API()
k = KrakenAPI(api)

def get_price(pair: str) -> float:
    """
    Obține ultimul preț de pe Kraken pentru un anumit pair (ex: 'XXBTZEUR').
    """
    try:
        data, _ = k.get_ticker_information(pair)
        return float(data['c'][0][0])
    except Exception as e:
        print(f"[get_price] Eroare: {e}")
        return None

def get_ohlc(pair: str, interval: int = 5) -> "pd.DataFrame":
    """
    Returnează un DataFrame cu date OHLC pentru analiza tehnică.
    """
    import pandas as pd
    try:
        ohlc, _ = k.get_ohlc_data(pair, interval=interval)
        ohlc = ohlc.rename(columns={
            "open": "open",
            "high": "high",
            "low": "low",
            "close": "close",
            "volume": "volume"
        })
        return ohlc
    except Exception as e:
        print(f"[get_ohlc] Eroare: {e}")
        return pd.DataFrame()

def place_market_order(pair: str, side: str, volume: float) -> dict:
    """
    Trimite un ordin de tip MARKET pe Kraken.
    """
    try:
        resp = api.query_private("AddOrder", {
            "pair": pair,
            "type": side,
            "ordertype": "market",
            "volume": str(volume)
        })
        if resp.get("error"):
            raise Exception(f"[place_market_order] Eroare Kraken: {resp['error']}")
        return resp
    except Exception as e:
        return {"error": str(e)}
