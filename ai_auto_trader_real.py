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
            CREATE TABLE IF NOT EXISTS {DB_SCHEMA}.signals (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMP NOT NULL,
                symbol TEXT NOT NULL,
                signal TEXT NOT NULL,
                price NUMERIC,
                risk_score NUMERIC,
                volatility NUMERIC
            )
        """))

        con.execute(text(f"""
            CREATE TABLE IF NOT EXISTS {DB_SCHEMA}.trades (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMP NOT NULL,
                symbol TEXT NOT NULL,
                action TEXT NOT NULL,
                quantity NUMERIC,
                price NUMERIC,
                profit_pct NUMERIC,
                status TEXT
            )
        """))

        con.execute(text(f"""
            CREATE TABLE IF NOT EXISTS {DB_SCHEMA}.prices (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMP NOT NULL,
                symbol TEXT NOT NULL,
                price NUMERIC
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
                total_profit NUMERIC
            )
        """))
    print(f"[{datetime.now()}] ✅ DB tables ready in schema {DB_SCHEMA}")

except Exception as e:
    print(f"[{datetime.now()}] ❌ DB connection error: {e}")
    conn = None

# -------------------- CONST & HELPERS --------------------
PAIR_TO_BAL_KEY = {
    "XXBTZEUR": "XXBT",
    "XETHZEUR": "XETH",
    "ADAEUR"  : "ADA",
}

MIN_ORDER_EUR = {"XXBTZEUR": 20.0, "XETHZEUR": 15.0, "ADAEUR": 5.0}
BALANCE_EPS   = 1e-12  # prag numeric ~0

def get_last_buy_sell(engine, symbol):
    """Returnează (last_buy_ts, last_buy_price, last_sell_ts)."""
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

def log_signal_db(simbol, semnal, pret, scor, volatilitate):
    if not conn:
        return
    try:
        with engine.begin() as con:
            con.execute(
                text(f"INSERT INTO {DB_SCHEMA}.signals (timestamp, symbol, signal, price, risk_score, volatility) "
                     "VALUES (:ts, :symbol, :signal, :price, :risk, :vol)"),
                {"ts": datetime.now(), "symbol": simbol, "signal": semnal,
                 "price": float(pret) if pret is not None else None,
                 "risk": float(scor) if scor is not None else None,
                 "vol": float(volatilitate) if volatilitate is not None else None}
            )
        print(f"[{datetime.now()}] ✅ Semnal salvat în DB: {simbol}={semnal}")
    except Exception as e:
        print(f"[{datetime.now()}] ❌ Eroare log_signal_db: {e}")

def log_trade_db(simbol, tip, cantitate, pret, profit_pct, status="EXECUTED"):
    if not conn:
        return
    try:
        with engine.begin() as con:
            con.execute(
                text(f"INSERT INTO {DB_SCHEMA}.trades (timestamp, symbol, action, quantity, price, profit_pct, status) "
                     "VALUES (:ts, :symbol, :action, :qty, :price, :profit, :status)"),
                {"ts": datetime.now(), "symbol": simbol, "action": tip,
                 "qty": float(cantitate) if cantitate is not None else None,
                 "price": float(pret) if pret is not None else None,
                 "profit": float(profit_pct) if profit_pct is not None else None,
                 "status": status}
            )
        print(f"[{datetime.now()}] 💾 Tranzacție salvată: {simbol} {tip} @ {pret:.6f} (qty={cantitate:.6f})")
    except Exception as e:
        print(f"[{datetime.now()}] ❌ Eroare log_trade_db: {e}")

def log_price_db(simbol, pret):
    if not conn:
        return
    try:
        with engine.begin() as con:
            con.execute(
                text(f"INSERT INTO {DB_SCHEMA}.prices (timestamp, symbol, price) VALUES (:ts, :symbol, :price)"),
                {"ts": datetime.now(), "symbol": simbol, "price": float(pret) if pret is not None else None}
            )
        print(f"[{datetime.now()}] ✅ Preț salvat în DB: {simbol}={pret}")
    except Exception as e:
        print(f"[{datetime.now()}] ❌ Eroare log_price_db: {e}")

def log_analysis_db(df):
    if not conn or df.empty:
        return
    try:
        with engine.begin() as con:
            for row in df.itertuples():
                con.execute(
                    text(f"""INSERT INTO {DB_SCHEMA}.analysis
                        (timestamp, symbol, buys, sells, avg_profit, total_profit)
                        VALUES (:ts, :symbol, :buys, :sells, :avg_profit, :total_profit)"""),
                    {"ts": datetime.now(), "symbol": row.symbol,
                     "buys": int(row.buys), "sells": int(row.sells),
                     "avg_profit": float(row.avg_profit) if row.avg_profit is not None else 0.0,
                     "total_profit": float(row.total_profit) if row.total_profit is not None else 0.0}
                )
        print(f"[{datetime.now()}] ✅ Analiza salvată pentru {len(df)} monede")
    except Exception as e:
        print(f"[{datetime.now()}] ❌ Eroare log_analysis_db: {e}")

# -------------------- STRATEGIE --------------------
def incarca_strategia():
    try:
        with open("strategy.json", "r") as f:
            strategie = json.load(f)
        print(f"[{datetime.now()}] ✅ Strategie încărcată din JSON: {strategie}")
        return strategie
    except Exception as e:
        print(f"[{datetime.now()}] ❌ Eroare încărcare strategy.json: {e}")
        # fallback sigur (mai defensiv)
        return {
            "symbols": ["XXBTZEUR", "XETHZEUR", "ADAEUR"],
            "allocations": {"XXBTZEUR": 0.45, "XETHZEUR": 0.45, "ADAEUR": 0.10},
            "RSI_Period": 10, "RSI_OB": 70, "RSI_OS": 30,
            "Stop_Loss": 2.0, "Take_Profit": 3.0, "Trailing_TP": 2.0
        }

# -------------------- SYNC POZIȚII (preia și monedele cumpărate manual) --------------------
def sincronizeaza_pozitii(pozitii, strategie):
    balans = get_balance()  # {'ADA': ..., 'XETH': ..., 'XXBT': ..., 'ZEUR': ...}
    print(f"[{datetime.now()}] 🔄 Resincronizare poziții...")
    for simbol in strategie.get("symbols", []):
        bal_key = PAIR_TO_BAL_KEY.get(simbol, simbol.replace("ZEUR",""))
        qty_on_exchange = float(balans.get(bal_key, 0.0))

        buy_ts, buy_px, sell_ts = get_last_buy_sell(engine, simbol)
        open_by_db = (buy_ts is not None) and (sell_ts is None or buy_ts > sell_ts)

        if qty_on_exchange > BALANCE_EPS:
            if open_by_db:
                # Poziție deschisă „oficial” în DB
                pozitii[simbol].update({
                    "deschis": True,
                    "pret_intrare": float(buy_px),
                    "cantitate": qty_on_exchange,
                    "max_profit": 0.0,
                    "trailing_active": False
                })
                print(f"[{datetime.now()}] 🔎 {simbol}: DB BUY @ {buy_px} (ts={buy_ts}) > SELL @ {sell_ts} → DESCHIS, qty={qty_on_exchange:.8f}")
            else:
                # Nu avem BUY activ în DB, dar avem cantitate în balanță → adoptăm poziția
                adopt_px = float(get_price(simbol))
                pozitii[simbol].update({
                    "deschis": True,
                    "pret_intrare": adopt_px,
                    "cantitate": qty_on_exchange,
                    "max_profit": 0.0,
                    "trailing_active": False
                })
                print(f"[{datetime.now()}] ⚠️ {simbol}: monedă detectată în balanță fără BUY activ în DB → adopt poziția la pret_intrare={adopt_px:.6f}, qty={qty_on_exchange:.8f}")
        else:
            pozitii[simbol].update({
                "deschis": False, "pret_intrare": 0.0, "cantitate": 0.0, "max_profit": 0.0, "trailing_active": False
            })
            reason = "qty≈0 în balans"
            print(f"[{datetime.now()}] 🔎 {simbol}: poziție ÎNCHISĂ ({reason}).")

# -------------------- BOT LOOP --------------------
def ruleaza_bot():
    strategie = incarca_strategia()
    balans_initial = get_balance()
    print(f"[{datetime.now()}] 🤖 Bot trading pornit!")
    print(f"[{datetime.now()}] 🔎 Balans inițial: {balans_initial}")

    pozitii = {s: {"deschis": False, "pret_intrare": 0.0, "cantitate": 0.0, "max_profit": 0.0, "trailing_active": False}
               for s in strategie.get("symbols", ["XXBTZEUR"])}

    sincronizeaza_pozitii(pozitii, strategie)
    next_analysis = datetime.now() + timedelta(hours=1)

    while True:
        try:
            balans = get_balance()
            eur_total = float(balans.get("ZEUR", 0.0))

            for simbol in strategie.get("symbols", ["XXBTZEUR"]):
                pret = get_price(simbol)
                semnal, scor, volatilitate = calculeaza_semnal(simbol, strategie)

                # log DB
                log_price_db(simbol, pret)
                log_signal_db(simbol, semnal, pret, scor, volatilitate)

                # poziția locală + cantitate reală de pe exchange
                p = pozitii[simbol]
                bal_key = PAIR_TO_BAL_KEY.get(simbol, simbol.replace("ZEUR",""))
                qty_on_exchange = float(balans.get(bal_key, 0.0))

                # watchdog: dacă era deschisă dar qty≈0, închide local
                if p["deschis"] and qty_on_exchange <= BALANCE_EPS:
                    print(f"[{datetime.now()}] ⚠️ {simbol}: marcat deschis dar qty≈0; marchez poziția ÎNCHISĂ.")
                    p.update({"deschis": False, "pret_intrare": 0.0, "cantitate": 0.0, "max_profit": 0.0, "trailing_active": False})

                # dimensionare ordin BUY
                eur_alocat = eur_total * float(strategie["allocations"].get(simbol, 0.0))
                eur_minim = MIN_ORDER_EUR.get(simbol, 15.0)
                if eur_alocat < eur_minim:
                    eur_alocat = eur_minim
                vol = (eur_alocat * 0.99) / pret if pret > 0 else 0.0

                # BUY pe semnal (doar dacă nu e deja poziție deschisă)
                if not p["deschis"] and semnal == "BUY":
                    if float(balans.get("ZEUR", 0)) < eur_alocat * 0.99:
                        print(f"[{datetime.now()}] ⛔ {simbol}: ZEUR insuficient pentru BUY (min≈{eur_alocat:.2f}€).")
                    else:
                        place_market_order("buy", vol, simbol)
                        p.update({"pret_intrare": pret, "cantitate": vol, "deschis": True, "max_profit": 0.0, "trailing_active": False})
                        log_trade_db(simbol, "BUY", vol, pret, 0.0)
                        print(f"[{datetime.now()}] ✅ ORDIN EXECUTAT: BUY {simbol} qty={vol:.6f} la {pret:.2f}")

                # SELL: TP / Trailing / SL
                elif p["deschis"]:
                    if p["pret_intrare"] <= 0:
                        print(f"[{datetime.now()}] ⚠️ {simbol}: pret_intrare invalid (0) → sar verificările SL/TP.")
                    else:
                        profit_pct = (pret - p["pret_intrare"]) / p["pret_intrare"] * 100.0
                        if profit_pct > p.get("max_profit", 0.0):
                            p["max_profit"] = profit_pct

                        # Activează trailing dacă s-a depășit TP
                        if not p.get("trailing_active", False) and p["max_profit"] >= float(strategie["Take_Profit"]):
                            p["trailing_active"] = True
                            print(f"[{datetime.now()}] 🏁 TRAILING ACTIV {simbol}: max_profit={p['max_profit']:.2f}% (TP={strategie['Take_Profit']}%)")

                        # DEBUG
                        print(f"[{datetime.now()}] 🧪 DEBUG {simbol}: pret_intrare={p['pret_intrare']:.6f} | "
                              f"pret_curent={pret:.6f} | profit_pct={profit_pct:.2f}% | "
                              f"max_profit={p['max_profit']:.2f}% | trailing_active={p['trailing_active']}")

                        # Take Profit fix
                        if profit_pct >= float(strategie["Take_Profit"]):
                            place_market_order("sell", p["cantitate"], simbol)
                            log_trade_db(simbol, "SELL_TP", p["cantitate"], pret, profit_pct)
                            p.update({"deschis": False, "max_profit": 0.0, "trailing_active": False})
                            print(f"[{datetime.now()}] ✅ SELL_TP {simbol} | Profit={profit_pct:.2f}%")

                        # Trailing TP (activ după ce a depășit TP)
                        elif p.get("trailing_active", False):
                            trailing = float(strategie.get("Trailing_TP", 2.0))
                            if profit_pct <= p["max_profit"] - trailing:
                                place_market_order("sell", p["cantitate"], simbol)
                                log_trade_db(simbol, "SELL_TRAILING", p["cantitate"], pret, profit_pct)
                                p.update({"deschis": False, "max_profit": 0.0, "trailing_active": False})
                                print(f"[{datetime.now()}] ✅ SELL_TRAILING {simbol} | Profit={profit_pct:.2f}%")

                        # Stop Loss
                        elif profit_pct <= -float(strategie["Stop_Loss"]):
                            place_market_order("sell", p["cantitate"], simbol)
                            log_trade_db(simbol, "SELL_SL", p["cantitate"], pret, profit_pct)
                            p.update({"deschis": False, "max_profit": 0.0, "trailing_active": False})
                            print(f"[{datetime.now()}] ✅ SELL_SL {simbol} | Profit={profit_pct:.2f}%")

            # Analiză periodică
            if datetime.now() >= next_analysis:
                try:
                    df_trades = pd.read_sql(f"SELECT * FROM {DB_SCHEMA}.trades", engine)
                    if not df_trades.empty:
                        summary = df_trades.groupby("symbol").agg(
                            buys=("action", lambda x: (x == "BUY").sum()),
                            sells=("action", lambda x: x.str.startswith("SELL").sum()),
                            avg_profit=("profit_pct", "mean"),
                            total_profit=("profit_pct", "sum"),
                        ).reset_index()
                        print(f"\n=== 💰 Analiză PnL @ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===")
                        print(summary)
                        log_analysis_db(summary)
                        print("===========================================\n")
                except Exception as e:
                    print(f"❌ Eroare la analiza automată: {e}")

                next_analysis = datetime.now() + timedelta(hours=1)

        except Exception as e:
            print(f"[{datetime.now()}] ❌ Eroare în rulare: {e}")

        time.sleep(10)

if __name__ == "__main__":
    ruleaza_bot()
