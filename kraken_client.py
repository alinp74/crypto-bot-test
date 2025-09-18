import datetime
import logging
import krakenex
from pykrakenapi import KrakenAPI

api = krakenex.API()
k = KrakenAPI(api)


def get_price(symbol: str):
    """Returnează (timestamp, price) pentru un simbol dat."""
    try:
        data = api.query_public("Ticker", {"pair": symbol})
        if data["error"]:
            logging.error(f"[get_price] Eroare Kraken: {data['error']}")
            return datetime.datetime.utcnow(), None

        result = list(data["result"].values())[0]
        price = float(result["c"][0])  # ultima cotație

        return datetime.datetime.utcnow(), price

    except Exception as e:
        logging.error(f"[get_price] Eroare pentru {symbol}: {e}")
        return datetime.datetime.utcnow(), None


def place_market_order(pair: str, side: str, volume: float):
    """Trimite un ordin market către Kraken."""
    try:
        logging.info(f"🔍 Kraken AddOrder request: side={side}, volume={volume}, pair={pair}")
        resp = api.query_private("AddOrder", {
            "pair": pair,
            "type": side,
            "ordertype": "market",
            "volume": str(volume)
        })
        if resp["error"]:
            raise Exception(f"[place_market_order] Eroare Kraken: {resp['error']}")

        logging.info(f"✅ Ordin executat: {resp}")
        return resp

    except Exception as e:
        logging.error(f"[place_market_order] Eroare: {e}")
        return None
