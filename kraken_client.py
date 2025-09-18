def get_price(k, pair: str):
    """Preia prețul curent de pe Kraken pentru un simbol."""
    try:
        data, _ = k.get_ticker_information(pair)
        return float(data["c"][0][0])
    except Exception as e:
        raise RuntimeError(f"[get_price] Eroare: {e}")


def place_market_order(api, pair: str, side: str, volume: float):
    """Trimite un ordin de tip market pe Kraken."""
    try:
        resp = api.query_private(
            "AddOrder",
            {
                "pair": pair,
                "type": side,
                "ordertype": "market",
                "volume": str(volume),
            },
        )
        if resp.get("error"):
            raise RuntimeError(f"[place_market_order] Eroare Kraken: {resp['error']}")
        return resp
    except Exception as e:
        raise RuntimeError(f"[place_market_order] Eroare: {e}")
