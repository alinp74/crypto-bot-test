import time
import json
import os
from datetime import datetime, timedelta
import pandas as pd
from sqlalchemy import create_engine, text
from kraken_client import get_price, get_balance, place_market_order
from strategie import calculeaza_semnal

print(f"[{datetime.now()}] 🚀 Bot started with SQLAlchemy...")

# -------------------- CONFIG --------------------
db_url = os.getenv("DATABASE_URL")
if db_url and db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)
DB_SCHEMA = os.getenv("DB_SCHEMA", "public")

PAIR_TO_BAL_KEY = {"XXBTZEUR": "XXBT", "XETHZEUR": "XETH"}
MIN_ORDER_EUR   = {"XXBTZEUR": 20.0, "XETHZEUR": 15.0}
FEE_RATE        = 0.0052   # ~0.26% buy + 0.26% sell
BALANCE_EPS     = 1e-12

# 🎯 Parametri anti-chop & DCA
DCA_DROP_PCT         = 5.0   # cumpără suplimentar dacă prețul a scăzut cu ≥5% față de media de intrare
REENTRY_COOLDOWN_SEC = 300   # 5 minute cooldown după vânzare
REENTRY_DROP_PCT     = 1.0   # re-intră doar dacă prețul e cu ≥1% sub ultimul preț de vânzare

# -------------------- DB INIT --------------------
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
            CREATE TABLE IF NOT EXISTS {DB_SCHEMA}.prices (
                id SERIAL PRIMARY KEY,
                timestamp TIMESTAMP NOT NULL,
                symbol TEXT NOT NULL,
                price NUMERIC
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
        # safety: coloane
        con.execute(text(f"ALTER TABLE {DB_SCHEMA}.trades   ADD COLUMN IF NOT EXISTS profit_eur NUMERIC;"))
        con.execute(text(f"ALTER TABLE {DB_SCHEMA}.analysis ADD COLUMN IF NOT EXISTS total_profit_eur NUMERIC;"))

    print(f"[{datetime.now()}] ✅ DB tables ready in schema {DB_SCHEMA}")
except Exception as e:
    print(f"[{datetime.now()}] ❌ DB connection error: {e}")
    conn = None

# -------------------- DB HELPERS --------------------
def log_signal_db(symbol, signal, price, risk, vol):
    if not conn: return
    try:
        with engine.begin() as con:
            con.execute(
                text(f"INSERT INTO {DB_SCHEMA}.signals (timestamp, symbol, signal, price, risk_score, volatility) "
                     "VALUES (:ts, :symbol, :signal, :price, :risk, :vol)"),
                {"ts": datetime.now(), "symbol": symbol, "signal": str(signal),
                 "price": float(price), "risk": float(risk) if risk is not None else None,
                 "vol": float(vol) if vol is not None else None}
            )
        print(f"[{datetime.now()}] ✅ Semnal salvat în DB: {symbol}={signal}")
    except Exception as e:
        print(f"[{datetime.now()}] ❌ Eroare log_signal_db: {e}")

def log_price_db(symbol, price):
    if not conn: return
    try:
        with engine.begin() as con:
            con.execute(
                text(f"INSERT INTO {DB_SCHEMA}.prices (timestamp, symbol, price) VALUES (:ts, :symbol, :price)"),
                {"ts": datetime.now(), "symbol": symbol, "price": float(price)}
            )
        print(f"[{datetime.now()}] ✅ Preț salvat în DB: {symbol}={price}")
    except Exception as e:
        print(f"[{datetime.now()}] ❌ Eroare log_price_db: {e}")

def log_trade_db(symbol, action, qty, price, profit_pct, profit_eur, status="EXECUTED"):
    if not conn: return
    try:
        with engine.begin() as con:
            con.execute(
                text(f"""
                    INSERT INTO {DB_SCHEMA}.trades
                    (timestamp, symbol, action, quantity, price, profit_pct, profit_eur, status)
                    VALUES (:ts, :symbol, :action, :qty, :price, :profit_pct, :profit_eur, :status)
                """),
                {"ts": datetime.now(), "symbol": symbol, "action": action,
                 "qty": float(qty), "price": float(price),
                 "profit_pct": float(profit_pct), "profit_eur": float(profit_eur),
                 "status": status}
            )
        print(f"[{datetime.now()}] 💾 Tranzacție salvată: {symbol} {action} @ {price:.2f}")
    except Exception as e:
        print(f"[{datetime.now()}] ❌ log_trade_db error: {e}")

def log_analysis_db(df):
    if not conn: return
    try:
        if df.empty:
            with engine.begin() as con:
                con.execute(
                    text(f"""
                        INSERT INTO {DB_SCHEMA}.analysis
                        (timestamp, symbol, buys, sells, avg_profit, total_profit, total_profit_eur)
                        VALUES (:ts, 'NONE', 0, 0, 0, 0, 0)
                    """), {"ts": datetime.now()}
                )
            print(f"[{datetime.now()}] ⏳ Analiză rulată – fără tranzacții noi.")
            return
        with engine.begin() as con:
            for row in df.itertuples():
                con.execute(
                    text(f"""
                        INSERT INTO {DB_SCHEMA}.analysis
                        (timestamp, symbol, buys, sells, avg_profit, total_profit, total_profit_eur)
                        VALUES (:ts, :symbol, :buys, :sells, :avg_profit, :total_profit, :total_profit_eur)
                    """),
                    {"ts": datetime.now(), "symbol": row.symbol,
                     "buys": int(row.buys), "sells": int(row.sells),
                     "avg_profit": float(row.avg_profit) if row.avg_profit is not None else 0.0,
                     "total_profit": float(row.total_profit) if row.total_profit is not None else 0.0,
                     "total_profit_eur": float(row.total_profit_eur) if row.total_profit_eur is not None else 0.0}
                )
        print(f"[{datetime.now()}] ✅ Analiză salvată ({len(df)} simboluri)")
    except Exception as e:
        print(f"[{datetime.now()}] ❌ Eroare log_analysis_db: {e}")

# -------------------- STRATEGIE --------------------
def incarca_strategia():
    try:
        with open("strategy.json", "r") as f:
            strat = json.load(f)
        print(f"[{datetime.now()}] ✅ Strategie încărcată: {strat}")
        return strat
    except Exception as e:
        print(f"[{datetime.now()}] ⚠️ Strategie implicită, eroare: {e}")
        return {
            "symbols": ["XXBTZEUR", "XETHZEUR"],
            "allocations": {"XXBTZEUR": 0.5, "XETHZEUR": 0.5},
            "RSI_Period": 7, "RSI_OB": 68, "RSI_OS": 30,
            "Stop_Loss": 0.0, "Take_Profit": 4.0, "Trailing_TP": 1.5
        }

# -------------------- POZIȚII --------------------
def sincronizeaza_pozitii(pozitii, strategie):
    balans = get_balance()
    print(f"[{datetime.now()}] 🔄 Resincronizare poziții...")
    for s in strategie.get("symbols", []):
        key = PAIR_TO_BAL_KEY.get(s, s.replace("ZEUR",""))
        qty = float(balans.get(key, 0.0))
        if qty > BALANCE_EPS:
            pret = float(get_price(s))
            pozitii[s] = {
                "deschis": True,
                "pret_intrare": pret,     # dacă vrei, poți înlocui cu ultimul BUY din DB
                "cantitate": qty,
                "max_profit": 0.0,
                "last_sell_time": None,
                "last_sell_price": None
            }
            print(f"[{datetime.now()}] 🔎 {s}: OPEN qty={qty}")
        else:
            pozitii[s] = {
                "deschis": False,
                "pret_intrare": 0.0,
                "cantitate": 0.0,
                "max_profit": 0.0,
                "last_sell_time": None,
                "last_sell_price": None
            }
            print(f"[{datetime.now()}] 🔒 {s}: fără poziție activă")

# -------------------- MAIN LOOP --------------------
def ruleaza_bot():
    strat = incarca_strategia()
    symbols = strat.get("symbols", ["XXBTZEUR","XETHZEUR"])
    pozitii = {s: {"deschis": False, "pret_intrare": 0.0, "cantitate": 0.0, "max_profit": 0.0,
                   "last_sell_time": None, "last_sell_price": None} for s in symbols}
    sincronizeaza_pozitii(pozitii, strat)

    next_analysis = datetime.now() + timedelta(minutes=15)

    while True:
        try:
            balans = get_balance()
            eur_avail = float(balans.get("ZEUR", 0.0))

            # împărțim EUR disponibili doar între simbolurile care NU sunt deschise (BUY) sau care cer DCA
            need_buy = []
            for s in symbols:
                p = pozitii[s]
                if not p["deschis"]:
                    need_buy.append(s)

            alloc_sum = sum(strat["allocations"].get(s, 0.0) for s in need_buy) or 0.0

            for s in symbols:
                pret = float(get_price(s))
                semnal, scor, vol = calculeaza_semnal(s, strat)

                # log preț + semnal
                log_price_db(s, pret)
                log_signal_db(s, semnal, pret, scor, vol)

                p = pozitii[s]

                # ---------------- MONITORIZARE / SELL (TP, Trailing, SL) ----------------
                if p["deschis"]:
                    # calculează profitul curent
                    profit_pct = ((pret - p["pret_intrare"]) / p["pret_intrare"] * 100.0) if p["pret_intrare"] > 0 else 0.0
                    profit_eur = (pret - p["pret_intrare"]) * p["cantitate"]
                    fee = (pret * p["cantitate"]) * FEE_RATE
                    net_profit_eur = profit_eur - fee

                    # actualizează max profit
                    if profit_pct > p["max_profit"]:
                        p["max_profit"] = profit_pct

                    # 🧪 log la fiecare iterație pentru toate pozițiile deschise
                    print(f"[{datetime.now()}] 🧪 {s}: profit={profit_pct:.2f}% | max={p['max_profit']:.2f}% | qty={p['cantitate']:.6f}")

                    # 1) Take Profit — doar prag pentru trailing
                    if profit_pct >= float(strat["Take_Profit"]):
                        print(f"[{datetime.now()}] ℹ️ TP REACHED {s}: profit {profit_pct:.2f}% — trailing activat")
                        pass

                    # 2) Trailing — vinde dacă avem retragere din vârf
                    if p["max_profit"] >= float(strat["Take_Profit"]) and \
                       profit_pct <= p["max_profit"] - float(strat["Trailing_TP"]):
                        place_market_order("sell", p["cantitate"], s)
                        log_trade_db(s, "SELL_TRAILING", p["cantitate"], pret, profit_pct, net_profit_eur)
                        p["deschis"] = False
                        p["max_profit"] = 0.0
                        p["last_sell_time"] = datetime.now()
                        p["last_sell_price"] = pret
                        print(f"[{datetime.now()}] ✅ VÂNZARE TRAILING: {s}")
                        continue

                    # 3) Stop-Loss
                    sl = float(strat.get("Stop_Loss", 0.0))
                    if sl > 0 and profit_pct <= -sl:
                        place_market_order("sell", p["cantitate"], s)
                        log_trade_db(s, "SELL_SL", p["cantitate"], pret, profit_pct, net_profit_eur)
                        p["deschis"] = False
                        p["max_profit"] = 0.0
                        p["last_sell_time"] = datetime.now()
                        p["last_sell_price"] = pret
                        print(f"[{datetime.now()}] ✅ VÂNZARE SL: {s}")
                        continue

                # ---------------- BUY LOGIC (poziție închisă) ----------------
                # (A) Re-entry guard: dacă am vândut recent, nu re-cumpărăm imediat și nu la preț mai mare
                can_reenter = True
                if p["last_sell_time"] is not None:
                    since = (datetime.now() - p["last_sell_time"]).total_seconds()
                    if since < REENTRY_COOLDOWN_SEC:
                        can_reenter = False
                    elif p["last_sell_price"] is not None:
                        # re-intră doar mai ieftin cu REENTRY_DROP_PCT
                        if pret > p["last_sell_price"] * (1.0 - REENTRY_DROP_PCT/100.0):
                            can_reenter = False

                # (B) Buy pe poziție închisă

                # PATCH: calculează trend EMA din DB (ultimele 400 prețuri)
                try:
                    with engine.connect() as con:
                        q = text(f"""
                            SELECT price FROM {DB_SCHEMA}.prices
                            WHERE symbol = :sym
                            ORDER BY timestamp DESC
                            LIMIT 400
                        """)
                        rows = con.execute(q, {"sym": s}).fetchall()
                        closes = pd.Series([float(r[0]) for r in rows][::-1])  # oldest -> newest
                        ema50 = closes.ewm(span=50, adjust=False).mean().iloc[-1]
                        ema200 = closes.ewm(span=200, adjust=False).mean().iloc[-1]
                        trend_ok = (ema50 > ema200)
                except Exception as _e:
                        trend_ok = False

                if (not p["deschis"]) and alloc_sum > 0 and (semnal == "BUY" or trend_ok) and can_reenter:
                    alloc = strat["allocations"].get(s, 0.0)
                    eur_target = eur_avail * (alloc / alloc_sum)
                    eur_min = MIN_ORDER_EUR.get(s, 15.0)
                    if eur_target < eur_min:
                        eur_target = eur_min

                    if eur_avail >= eur_target * 0.99 and pret > 0:
                        qty = (eur_target * 0.99) / pret
                        place_market_order("buy", qty, s)
                        p.update({"deschis": True, "pret_intrare": pret, "cantitate": qty, "max_profit": 0.0})
                        log_trade_db(s, "BUY", qty, pret, 0.0, 0.0)
                        eur_avail -= eur_target
                        print(f"[{datetime.now()}] ✅ CUMPĂRARE: {s} qty={qty:.6f} @ {pret:.2f} | EUR_spent≈{eur_target:.2f}")
                    else:
                        print(f"[{datetime.now()}] ⛔ {s}: ZEUR insuficient (need≈{eur_target:.2f}, avail≈{eur_avail:.2f})")

                # ---------------- DCA (poziție deschisă) ----------------
                elif p["deschis"]:
                    # DCA doar între -DCA_DROP_PCT și pragul de Stop-Loss
                    drop_pct = ( (p["pret_intrare"] - pret) / p["pret_intrare"] * 100.0 ) if p["pret_intrare"] > 0 else 0.0

                    # DCA eligibil: scădere >= DCA_DROP_PCT și NU suntem sub SL
                    if drop_pct >= DCA_DROP_PCT:
                        # dacă profitul actual e deja sub SL, NU mai face DCA (SL a fost deja rulat mai sus)
                        sl = float(strat.get("Stop_Loss", 0.0))
                        if sl > 0 and cur_profit_pct <= -sl:
                        # SL a fost tratat mai sus; nu DCA aici
                            continue

                        # fonduri suficiente?
                        eur_min = MIN_ORDER_EUR.get(s, 15.0)
                        if eur_avail < eur_min:
                            print(f"[{datetime.now()}] ⚠️ Fonduri insuficiente pentru DCA {s} — sar peste (avail={eur_avail:.2f}€, min={eur_min:.2f}€).")
                            # nu blochez bucla; merg mai departe
                            pass
                        else:
                            # alocă până la greutatea simbolului, din EUR_avail
                            alloc_eur = min(eur_avail, strat["allocations"].get(s, 0.5) * max(eur_avail, 0))
                            eur_to_spend = max(eur_min, min(alloc_eur, eur_avail))
                            if eur_to_spend > 0 and pret > 0:
                                add_qty = (eur_to_spend * 0.99) / pret
                                place_market_order("buy", add_qty, s)
                                # medie ponderată a prețului de intrare
                                new_qty = p["cantitate"] + add_qty
                                new_avg = ((p["pret_intrare"] * p["cantitate"]) + (pret * add_qty)) / new_qty
                                p.update({"pret_intrare": new_avg, "cantitate": new_qty})
                                log_trade_db(s, "BUY_DCA", add_qty, pret, 0.0, 0.0)
                                eur_avail -= eur_to_spend
                                print(f"[{datetime.now()}] 🔄 DCA BUY: {s} +{add_qty:.6f} @ {pret:.2f} | avg={new_avg:.2f}")
                    # altfel: nu face DCA

            # 📊 ANALIZA LA 15 MINUTE (chiar și fără tranzacții)
            if datetime.now() >= next_analysis:
                try:
                    df = pd.read_sql(f"SELECT * FROM {DB_SCHEMA}.trades", engine)
                    if df.empty:
                        log_analysis_db(pd.DataFrame())
                    else:
                        summary = df.groupby("symbol").agg(
                            buys=("action", lambda x: (x == "BUY").sum() + (x == "BUY_DCA").sum()),
                            sells=("action", lambda x: x.str.startswith("SELL").sum()),
                            avg_profit=("profit_pct", "mean"),
                            total_profit=("profit_pct", "sum"),
                            total_profit_eur=("profit_eur", "sum")
                        ).reset_index()
                        print(f"\n=== 💰 Analiză @ {datetime.now()} ===\n{summary}\n")
                        log_analysis_db(summary)
                except Exception as e:
                    print(f"❌ Eroare analiză: {e}")

                next_analysis = datetime.now() + timedelta(minutes=15)

        except Exception as e:
            print(f"[{datetime.now()}] ❌ Loop error: {e}")

        time.sleep(10)

if __name__ == "__main__":
    ruleaza_bot()
