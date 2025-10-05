import time
import json
import os
from datetime import datetime, timedelta
import pandas as pd
from sqlalchemy import create_engine, text
from kraken_client import get_price, get_balance, place_market_order
from strategie import calculeaza_semnal

print(f"[{datetime.now()}] 🚀 Bot started with SQLAlchemy...")

# -------------------- DB INIT --------------------
db_url = os.getenv("DATABASE_URL")
if db_url and db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

DB_SCHEMA = os.getenv("DB_SCHEMA", "public")

try:
    engine = create_engine(db_url)
    conn = engine.connect()
    print(f"[{datetime.now()}] ✅ Connected to Postgres (schema={DB_SCHEMA})")

    with engine.begin() as con:
        con.execute(text(f"CREATE SCHEMA IF NOT EXISTS {DB_SCHEMA};"))

        con.execute(text(f"""
            CREATE TABLE IF NOT EXISTS {DB_SCHEMA}.trades (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMP NOT NULL,
                symbol TEXT NOT NULL,
                action TEXT NOT NULL,
                quantity NUMERIC,
                price NUMERIC,
                profit_pct NUMERIC,
                profit_eur NUMERIC,
                status TEXT
            )
        """))

        con.execute(text(f"""
            CREATE TABLE IF NOT EXISTS {DB_SCHEMA}.analysis (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMP NOT NULL,
                symbol TEXT NOT NULL,
                buys INT,
                sells INT,
                avg_profit NUMERIC,
                total_profit NUMERIC,
                total_profit_eur NUMERIC
            )
        """))
    print(f"[{datetime.now()}] ✅ DB tables ready in schema {DB_SCHEMA}")

except Exception as e:
    print(f"[{datetime.now()}] ❌ DB connection error: {e}")
    conn = None

# -------------------- CONST --------------------
PAIR_TO_BAL_KEY = {"XXBTZEUR": "XXBT", "XETHZEUR": "XETH"}
MIN_ORDER_EUR   = {"XXBTZEUR": 20.0, "XETHZEUR": 15.0}
FEE_RATE        = 0.0052  # 0.26% buy + 0.26% sell
BALANCE_EPS     = 1e-12

# -------------------- HELPERS --------------------
def get_last_buy_sell(engine, symbol):
    last_buy = pd.read_sql(
        f"SELECT timestamp, price FROM {DB_SCHEMA}.trades "
        f"WHERE symbol=%(s)s AND action='BUY' ORDER BY timestamp DESC LIMIT 1",
        engine, params={"s": symbol}
    )
    last_sell = pd.read_sql(
        f"SELECT timestamp FROM {DB_SCHEMA}.trades "
        f"WHERE symbol=%(s)s AND action LIKE 'SELL%%' ORDER BY timestamp DESC LIMIT 1",
        engine, params={"s": symbol}
    )
    buy_ts = pd.to_datetime(last_buy.iloc[0]["timestamp"]) if not last_buy.empty else None
    buy_px = float(last_buy.iloc[0]["price"]) if not last_buy.empty else None
    sell_ts = pd.to_datetime(last_sell.iloc[0]["timestamp"]) if not last_sell.empty else None
    return buy_ts, buy_px, sell_ts


def log_trade_db(symbol, action, qty, price, profit_pct, profit_eur, status="EXECUTED"):
    if not conn:
        return
    try:
        with engine.begin() as con:
            con.execute(
                text(f"""
                    INSERT INTO {DB_SCHEMA}.trades 
                    (timestamp, symbol, action, quantity, price, profit_pct, profit_eur, status)
                    VALUES (:ts, :symbol, :action, :qty, :price, :profit_pct, :profit_eur, :status)
                """),
                {
                    "ts": datetime.now(), "symbol": symbol, "action": action,
                    "qty": float(qty), "price": float(price),
                    "profit_pct": float(profit_pct), "profit_eur": float(profit_eur),
                    "status": status
                }
            )
        print(f"[{datetime.now()}] 💾 Trade logged: {symbol} {action} @ {price:.2f} | {profit_pct:.2f}% | {profit_eur:.2f}€")
    except Exception as e:
        print(f"[{datetime.now()}] ❌ log_trade_db error: {e}")


def log_analysis_db(df):
    if not conn or df.empty:
        return
    try:
        with engine.begin() as con:
            for row in df.itertuples():
                con.execute(
                    text(f"""
                        INSERT INTO {DB_SCHEMA}.analysis 
                        (timestamp, symbol, buys, sells, avg_profit, total_profit, total_profit_eur)
                        VALUES (:ts, :symbol, :buys, :sells, :avg_profit, :total_profit, :total_profit_eur)
                    """),
                    {
                        "ts": datetime.now(), "symbol": row.symbol,
                        "buys": int(row.buys), "sells": int(row.sells),
                        "avg_profit": float(row.avg_profit),
                        "total_profit": float(row.total_profit),
                        "total_profit_eur": float(row.total_profit_eur)
                    }
                )
        print(f"[{datetime.now()}] ✅ Analysis updated for {len(df)} symbols")
    except Exception as e:
        print(f"[{datetime.now()}] ❌ log_analysis_db error: {e}")


def incarca_strategia():
    try:
        with open("strategy.json", "r") as f:
            strat = json.load(f)
        print(f"[{datetime.now()}] ✅ Strategy loaded: {strat}")
        return strat
    except:
        return {
            "symbols": ["XXBTZEUR", "XETHZEUR"],
            "allocations": {"XXBTZEUR": 0.5, "XETHZEUR": 0.5},
            "RSI_Period": 10, "RSI_OB": 70, "RSI_OS": 30,
            "Stop_Loss": 2.0, "Take_Profit": 3.0, "Trailing_TP": 2.0
        }


def sincronizeaza_pozitii(pozitii, strategie):
    balans = get_balance()
    print(f"[{datetime.now()}] 🔄 Resincronizare poziții...")
    for s in strategie.get("symbols", []):
        key = PAIR_TO_BAL_KEY.get(s, s.replace("ZEUR", ""))
        qty = float(balans.get(key, 0.0))
        buy_ts, buy_px, sell_ts = get_last_buy_sell(engine, s)
        open_db = (buy_ts is not None) and (sell_ts is None or buy_ts > sell_ts)

        if qty > BALANCE_EPS:
            if open_db:
                pozitii[s] = {"deschis": True, "pret_intrare": float(buy_px), "cantitate": qty, "max_profit": 0.0}
                print(f"[{datetime.now()}] 🔎 {s}: OPEN @ {buy_px} qty={qty}")
            else:
                adopt_px = float(get_price(s))
                pozitii[s] = {"deschis": True, "pret_intrare": adopt_px, "cantitate": qty, "max_profit": 0.0}
                print(f"[{datetime.now()}] ⚠️ {s}: adopt poziția manuală @ {adopt_px}")
        else:
            pozitii[s] = {"deschis": False, "pret_intrare": 0, "cantitate": 0, "max_profit": 0.0}
            print(f"[{datetime.now()}] 🔒 {s}: fără poziție activă")


# -------------------- BOT LOOP --------------------
def ruleaza_bot():
    strat = incarca_strategia()
    pozitii = {s: {"deschis": False, "pret_intrare": 0, "cantitate": 0, "max_profit": 0.0}
               for s in strat.get("symbols", [])}
    sincronizeaza_pozitii(pozitii, strat)

    next_analysis = datetime.now() + timedelta(hours=1)

    while True:
        try:
            balans = get_balance()
            eur_total = float(balans.get("ZEUR", 0.0))
            eur_disponibil = eur_total

            for s in strat["symbols"]:
                pret = get_price(s)
                semnal, scor, vol = calculeaza_semnal(s, strat)
                p = pozitii[s]

                if not p["deschis"] and semnal == "BUY":
                    eur_target = eur_total * strat["allocations"].get(s, 0.0)
                    if eur_target < MIN_ORDER_EUR.get(s, 15.0):
                        eur_target = MIN_ORDER_EUR[s]

                    if eur_disponibil >= eur_target * 0.99:
                        qty = (eur_target * 0.99) / pret
                        place_market_order("buy", qty, s)
                        p.update({"deschis": True, "pret_intrare": pret, "cantitate": qty, "max_profit": 0.0})
                        log_trade_db(s, "BUY", qty, pret, 0.0, 0.0)
                        eur_disponibil -= eur_target
                        print(f"[{datetime.now()}] ✅ BUY {s} {qty:.6f} @ {pret:.2f} (EUR_spent={eur_target:.2f})")

                elif p["deschis"]:
                    profit_pct = (pret - p["pret_intrare"]) / p["pret_intrare"] * 100.0
                    profit_eur = (pret - p["pret_intrare"]) * p["cantitate"]
                    fee = (pret * p["cantitate"]) * FEE_RATE
                    net_profit_eur = profit_eur - fee

                    if profit_pct > p["max_profit"]:
                        p["max_profit"] = profit_pct

                    print(f"[{datetime.now()}] 🧪 {s}: profit={profit_pct:.2f}% | max={p['max_profit']:.2f}% | net={net_profit_eur:.2f}€")

                    # SELL logic
                    if profit_pct >= strat["Take_Profit"]:
                        place_market_order("sell", p["cantitate"], s)
                        log_trade_db(s, "SELL_TP", p["cantitate"], pret, profit_pct, net_profit_eur)
                        p.update({"deschis": False, "max_profit": 0.0})
                        print(f"[{datetime.now()}] ✅ SELL_TP {s}")

                    elif p["max_profit"] >= strat["Take_Profit"] and profit_pct <= p["max_profit"] - strat["Trailing_TP"]:
                        place_market_order("sell", p["cantitate"], s)
                        log_trade_db(s, "SELL_TRAILING", p["cantitate"], pret, profit_pct, net_profit_eur)
                        p.update({"deschis": False, "max_profit": 0.0})
                        print(f"[{datetime.now()}] ✅ SELL_TRAILING {s}")

                    elif profit_pct <= -strat["Stop_Loss"]:
                        place_market_order("sell", p["cantitate"], s)
                        log_trade_db(s, "SELL_SL", p["cantitate"], pret, profit_pct, net_profit_eur)
                        p.update({"deschis": False, "max_profit": 0.0})
                        print(f"[{datetime.now()}] ✅ SELL_SL {s}")

            # periodic analysis
            if datetime.now() >= next_analysis:
                try:
                    df = pd.read_sql(f"SELECT * FROM {DB_SCHEMA}.trades", engine)
                    if not df.empty:
                        summary = df.groupby("symbol").agg(
                            buys=("action", lambda x: (x == "BUY").sum()),
                            sells=("action", lambda x: x.str.startswith("SELL").sum()),
                            avg_profit=("profit_pct", "mean"),
                            total_profit=("profit_pct", "sum"),
                            total_profit_eur=("profit_eur", "sum")
                        ).reset_index()
                        print(f"=== 💰 Summary @ {datetime.now()} ===\n{summary}")
                        log_analysis_db(summary)
                except Exception as e:
                    print(f"❌ Eroare analiză: {e}")

                next_analysis = datetime.now() + timedelta(hours=1)

        except Exception as e:
            print(f"[{datetime.now()}] ❌ Loop error: {e}")
        time.sleep(10)


if __name__ == "__main__":
    ruleaza_bot()
