import os
import krakenex
from pykrakenapi import KrakenAPI

# Inițializare API
api = krakenex.API(
    key=os.getenv("KRAKEN_API_KEY"),
    secret=os.getenv("KRAKEN_API_SECRET")
)
k = KrakenAPI(api)


def get_price(symbol):
    """Ultimul preț pentru un simbol"""
    try:
        data, _ = k.get_ticker_information(symbol)
        return float(data["c"].iloc[0][0])  # prețul last trade close
    except Exception as e:
        print(f"[get_price] Eroare: {e}")
        return None


def get_balance():
    """Balans cont Kraken"""
    try:
        return k.get_account_balance()
    except Exception as e:
        print(f"[get_balance] Eroare: {e}")
        return {}


def get_balance_qty(symbol):
    """Cantitatea pentru un simbol (ex: XXBT, XETH, ADA)"""
    try:
        balans = get_balance()
        asset = symbol.replace("EUR", "").replace("Z", "").replace("X", "")
        for key in balans.index:
            if asset in key:
                return float(balans[key])
        return 0.0
    except Exception as e:
        print(f"[get_balance_qty] Eroare: {e}")
        return 0.0


def place_market_order(symbol, side, volume):
    """Plasare ordin market (BUY/SELL)"""
    try:
        resp = k.add_standard_order(
            pair=symbol,
            type=side,
            ordertype="market",
            volume=volume
        )
        print(f"🔍 Kraken AddOrder response: {resp}")
        return resp
    except Exception as e:
        print(f"[place_market_order] Eroare: {e}")
        return {"error": [str(e)]}


def get_total_capital():
    """Calculează capitalul total EUR (crypto + cash)"""
    balans = get_balance()
    total = 0.0
    for asset, row in balans.items():
        try:
            if asset == "ZEUR":
                total += float(row)
            else:
                pair = f"{asset}EUR" if asset.startswith("X") or asset.startswith("Z") else f"X{asset}ZEUR"
                price = get_price(pair)
                if price:
                    total += float(row) * price
        except Exception:
            continue
    return total


def calc_order_size(symbol, price, capital_total):
    """Calculează volumul ordinului"""
    try:
        min_order_size = 0.0001  # fallback
        return max(capital_total / price, min_order_size)
    except Exception as e:
        print(f"[calc_order_size] Eroare: {e}")
        return 0.0


def get_ohlc(symbol, interval=15, lookback=200):
    """Preia date OHLC de pe Kraken pentru strategie"""
    try:
        df, _ = k.get_ohlc_data(symbol, interval=interval)
        return df.tail(lookback)
    except Exception as e:
        print(f"[get_ohlc] Eroare: {e}")
        return None
