import krakenex
from pykrakenapi import KrakenAPI
import pandas as pd

api = krakenex.API()
k = KrakenAPI(api)

def get_price(pair):
    try:
        data = k.get_ticker_information(pair)
        if "c" in data:
            return float(data["c"][0])
        return None
    except Exception as e:
        print(f"[get_price] Eroare: {e}")
        return None

def get_ohlc(pair, interval=5, since=None):
    try:
        ohlc, last = k.get_ohlc_data(pair, interval=interval, since=since)
        if ohlc is None or ohlc.empty:
            return None
        ohlc = ohlc[["time", "open", "high", "low", "close", "volume"]].copy()
        ohlc["time"] = pd.to_datetime(ohlc.index, unit="s")
        return ohlc
    except Exception as e:
        print(f"[get_ohlc] Eroare: {e}")
        return None

def get_balance():
    try:
        balance = k.get_account_balance()
        return {k: float(v) for k, v in balance.items()}
    except Exception as e:
        print(f"[get_balance] Eroare: {e}")
        return {}

def place_market_order(pair, side, volume):
    try:
        resp = k.add_standard_order(
            pair=pair,
            type=side.lower(),
            ordertype="market",
            volume=volume
        )
        if resp and "result" in resp and "txid" in resp["result"]:
            return resp["result"]["txid"][0]
        return None
    except Exception as e:
        print(f"[place_market_order] Eroare: {e}")
        return None
