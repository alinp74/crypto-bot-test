import os
import json
import pandas as pd
from dotenv import load_dotenv
from binance.client import Client
import ta
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objs as go
from datetime import datetime

# === CONFIG ===
load_dotenv()
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
SYMBOL = "BTCUSDT"

client = Client(API_KEY, API_SECRET)
client.API_URL = "https://testnet.binance.vision/api"  # Testnet pentru siguranță

# === PARAMETRI RISC ===
STOP_LOSS = 2.0       # %
TAKE_PROFIT = 3.0     # %
MAX_TRADES_PER_DAY = 5
MAX_DAILY_LOSS = 50.0  # USDT

app = dash.Dash(__name__, suppress_callback_exceptions=True)
app.title = "Crypto AI Trading Dashboard Pro"

# === DESCĂRCARE DATE ===
def get_historical(interval="15m", period="7 days ago UTC"):
    klines = client.get_historical_klines(SYMBOL, interval, period)
    df = pd.DataFrame(klines, columns=[
        "timestamp", "open", "high", "low", "close", "volume",
        "close_time", "qav", "num_trades", "tbbav", "tbqav", "ignore"
    ])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df["close"] = df["close"].astype(float)
    df["open"] = df["open"].astype(float)
    df["high"] = df["high"].astype(float)
    df["low"] = df["low"].astype(float)
    return df

# === ÎNCĂRCARE STRATEGIE ===
def load_strategy():
    if os.path.exists("strategy.json"):
        with open("strategy.json", "r") as f:
            return json.load(f)
    return None

# === SEMNAL LIVE ===
def get_live_signal(strategy):
    df = get_historical(interval="15m", period="7 days ago UTC")
    df["rsi"] = ta.momentum.RSIIndicator(df["close"], window=int(strategy["RSI_Period"])).rsi()
    macd = ta.trend.MACD(
        df["close"],
        window_slow=int(strategy["MACD_Slow"]),
        window_fast=int(strategy["MACD_Fast"]),
        window_sign=int(strategy["MACD_Signal"])
    )
    df["macd"] = macd.macd()
    df["signal"] = macd.macd_signal()
    df = df.dropna()

    last_rsi = df["rsi"].iloc[-1]
    last_macd = df["macd"].iloc[-1]
    last_signal = df["signal"].iloc[-1]

    if last_rsi < float(strategy["RSI_OS"]) and last_macd > last_signal:
        return "🟢 CUMPĂRĂ"
    elif last_rsi > float(strategy["RSI_OB"]) and last_macd < last_signal:
        return "🔴 VINDE"
    else:
        return "⏳ Așteaptă"

# === SOLD WALLET ===
def get_wallet_balance():
    try:
        balances = client.get_account()["balances"]
        btc = next(item for item in balances if item["asset"] == "BTC")
        usdt = next(item for item in balances if item["asset"] == "USDT")
        return float(btc["free"]), float(usdt["free"])
    except:
        return 0.0, 0.0

# === CITIRE ISTORIC TRANZACȚII ===
def get_trade_history():
    if os.path.exists("trade_log.json"):
        with open("trade_log.json", "r") as f:
            trades = json.load(f)
        trades.reverse()
        return trades
    return []

# === CALCUL PNL ===
def calculate_pnl(trades):
    pnl = sum(t.get("pnl", 0) for t in trades)
    return round(pnl, 2)

# === NUMĂR TRANZACȚII ZILNICE ===
def count_daily_trades(trades):
    today = datetime.now().strftime("%Y-%m-%d")
    return len([t for t in trades if t["time"].startswith(today)])

# === LAYOUT ===
app.layout = html.Div([
    html.H1("🤖 Dashboard AI Trading PRO", style={'textAlign': 'center'}),

    html.Div(id="strategy-box", style={'fontSize': 18, 'marginBottom': '15px'}),
    html.Div(id="live-signal", style={'fontSize': 22, 'fontWeight': 'bold', 'marginBottom': '15px'}),
    html.Div(id="wallet-balance", style={'fontSize': 18, 'marginBottom': '15px'}),
    html.Div(id="pnl-display", style={'fontSize': 20, 'marginBottom': '15px'}),
    html.Div(id="risk-status", style={'fontSize': 18, 'color': 'red', 'marginBottom': '20px'}),

    dcc.Graph(id="price-chart", style={'height': '500px'}),

    html.H3("📜 Istoric Tranzacții"),
    html.Div(id="trade-history", style={'whiteSpace': 'pre-line', 'fontSize': 16}),

    dcc.Interval(id="interval-update", interval=15*1000, n_intervals=0)
])

# === CALLBACK PRINCIPAL ===
@app.callback(
    [Output("strategy-box", "children"),
     Output("live-signal", "children"),
     Output("wallet-balance", "children"),
     Output("pnl-display", "children"),
     Output("risk-status", "children"),
     Output("price-chart", "figure"),
     Output("trade-history", "children")],
    [Input("interval-update", "n_intervals")]
)
def update_dashboard(n):
    strategy = load_strategy()
    trades = get_trade_history()
    btc, usdt = get_wallet_balance()

    if not strategy:
        return (
            "⚠️ Nu există strategie optimă. Rulează auto_optimizer.py.",
            "❌",
            f"BTC: {btc} | USDT: {usdt}",
            "Profit total: 0 USDT",
            "",
            go.Figure(),
            "Nicio tranzacție executată."
        )

    # Semnal live
    live_signal = get_live_signal(strategy)

    # PNL total
    pnl = calculate_pnl(trades)

    # Status risc
    daily_trades = count_daily_trades(trades)
    risk_status = ""
    if daily_trades >= MAX_TRADES_PER_DAY:
        risk_status = "⚠️ Limită tranzacții zilnice atinsă! Botul este oprit."
    elif pnl <= -MAX_DAILY_LOSS:
        risk_status = "🚨 Pierdere zilnică maximă atinsă! Botul este oprit."

    # Grafic BTC
    df = get_historical(interval="15m", period="7 days ago UTC")
    fig = go.Figure(data=[go.Candlestick(
        x=df["timestamp"],
        open=df["open"],
        high=df["high"],
        low=df["low"],
        close=df["close"],
        name="BTC/USDT"
    )])
    fig.update_layout(title="📈 Evoluție BTC/USDT", xaxis_rangeslider_visible=False)

    # Istoric tranzacții
    if trades:
        history_text = "\n".join([
            f"{t['time']} | {t['action']} | Entry: {t['entry_price']} | Exit: {t.get('exit_price', '-') } | PNL: {t['pnl']}"
            for t in trades
        ])
    else:
        history_text = "Nicio tranzacție executată încă."

    strategy_info = (
        f"📌 Strategia Curentă:\n"
        f"RSI_Period: {strategy['RSI_Period']} | RSI_OB: {strategy['RSI_OB']} | RSI_OS: {strategy['RSI_OS']}\n"
        f"MACD_Fast: {strategy['MACD_Fast']} | MACD_Slow: {strategy['MACD_Slow']} | MACD_Signal: {strategy['MACD_Signal']}\n"
        f"Profit Estimat: {round(float(strategy['Profit']), 2)} USDT\n"
        f"Ultima Optimizare: {strategy['Updated']}"
    )

    return strategy_info, live_signal, f"BTC: {btc} | USDT: {usdt}", f"Profit total: {pnl} USDT", risk_status, fig, history_text

# === RUN APP ===
if __name__ == "__main__":
    app.run(debug=True)
