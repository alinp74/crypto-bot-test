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

# === CONFIG ===
load_dotenv()
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
SYMBOL = "BTCUSDT"

client = Client(API_KEY, API_SECRET)
client.API_URL = "https://testnet.binance.vision/api"  # Testnet pentru siguranță

app = dash.Dash(__name__, suppress_callback_exceptions=True)
app.title = "Crypto AI Trading Dashboard"

# === FUNCȚIE DESCĂRCARE DATE ===
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

# === CITIRE STRATEGIE ===
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
        return "⏳ Așteaptă oportunitatea"

# === SOLD WALLET ===
def get_wallet_balance():
    try:
        balances = client.get_account()["balances"]
        btc = next(item for item in balances if item["asset"] == "BTC")
        usdt = next(item for item in balances if item["asset"] == "USDT")
        return f"BTC: {btc['free']} | USDT: {usdt['free']}"
    except:
        return "⚠️ Nu am putut obține soldul."

# === CITIRE ISTORIC TRANZACȚII ===
def get_trade_history():
    if os.path.exists("trade_log.json"):
        with open("trade_log.json", "r") as f:
            trades = json.load(f)
        trades.reverse()
        return trades
    return []

# === LAYOUT ===
app.layout = html.Div([
    html.H1("🤖 Dashboard AI Trading", style={'textAlign': 'center'}),

    # === STRATEGIE ===
    html.Div(id="strategy-box", style={'fontSize': 18, 'marginBottom': '15px'}),

    # === SEMNAL LIVE ===
    html.Div(id="live-signal", style={'fontSize': 24, 'fontWeight': 'bold', 'marginBottom': '15px'}),

    # === SOLD WALLET ===
    html.Div(id="wallet-balance", style={'fontSize': 18, 'marginBottom': '20px'}),

    # === GRAFIC BTC ===
    dcc.Graph(id="price-chart", style={'height': '500px'}),

    # === ISTORIC TRANZACȚII ===
    html.H3("📜 Tranzacții Executate"),
    html.Div(id="trade-history", style={'whiteSpace': 'pre-line', 'fontSize': 16}),

    # Actualizare automată la 15 secunde
    dcc.Interval(id="interval-update", interval=15*1000, n_intervals=0)
])

# === CALLBACK PRINCIPAL ===
@app.callback(
    [Output("strategy-box", "children"),
     Output("live-signal", "children"),
     Output("wallet-balance", "children"),
     Output("price-chart", "figure"),
     Output("trade-history", "children")],
    [Input("interval-update", "n_intervals")]
)
def update_dashboard(n):
    strategy = load_strategy()
    if not strategy:
        return (
            "⚠️ Nu există strategie optimă. Rulează auto_optimizer.py mai întâi.",
            "❌",
            get_wallet_balance(),
            go.Figure(),
            "Nicio tranzacție executată."
        )

    # Semnal live
    live_signal = get_live_signal(strategy)

    # Sold wallet
    balance = get_wallet_balance()

    # Grafic preț BTC
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
    trades = get_trade_history()
    if trades:
        history_text = "\n".join([
            f"{t['time']} | {t['action']} | Preț: {t['price']} | Cantitate: {t['quantity']}"
            for t in trades
        ])
    else:
        history_text = "Nicio tranzacție executată încă."

    # Strategie curentă
    strategy_info = (
        f"📌 Strategia Curentă:\n"
        f"RSI_Period: {strategy['RSI_Period']} | RSI_OB: {strategy['RSI_OB']} | RSI_OS: {strategy['RSI_OS']}\n"
        f"MACD_Fast: {strategy['MACD_Fast']} | MACD_Slow: {strategy['MACD_Slow']} | MACD_Signal: {strategy['MACD_Signal']}\n"
        f"Profit Estimat: {round(float(strategy['Profit']), 2)} USDT\n"
        f"Ultima Optimizare: {strategy['Updated']}"
    )

    return strategy_info, live_signal, balance, fig, history_text

# === RUN APP ===
if __name__ == "__main__":
    app.run(debug=True)
