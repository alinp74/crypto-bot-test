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
from itertools import product

# === CONFIG ===
load_dotenv()
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
SYMBOL = "BTCUSDT"

client = Client(API_KEY, API_SECRET)
client.API_URL = "https://api.binance.com/api"

# === DASHBOARD ===
app = dash.Dash(__name__, suppress_callback_exceptions=True)
app.title = "Crypto Bot - AI Dashboard"

# === FUNCȚIE DESCĂRCARE DATE ===
def get_historical(interval="15m", period="90 days ago UTC"):
    klines = client.get_historical_klines(SYMBOL, interval, period)
    df = pd.DataFrame(klines, columns=[
        "timestamp", "open", "high", "low", "close", "volume",
        "close_time", "qav", "num_trades", "tbbav", "tbqav", "ignore"
    ])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df["close"] = df["close"].astype(float)
    return df

# === CITIRE STRATEGIE OPTIMĂ ===
def load_strategy():
    if os.path.exists("strategy.json"):
        with open("strategy.json", "r") as f:
            return json.load(f)
    return None

# === CALCUL SEMNAL LIVE ===
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

# === LAYOUT ===
app.layout = html.Div([
    html.H1("🤖 Dashboard AI Trading", style={'textAlign': 'center'}),

    # === STRATEGIE OPTIMĂ ===
    html.Div([
        html.H3("📌 Strategia Optimizată Curentă"),
        html.Div(id="strategy-box", style={'fontSize': 18, 'marginBottom': '20px'})
    ]),

    # === SEMNAL LIVE ===
    html.Div([
        html.H3("🔔 Semnal Live"),
        html.Div(id="live-signal", style={'fontSize': 22, 'fontWeight': 'bold', 'color': '#00B050'})
    ]),

    # === GRAFIC LIVE ===
    dcc.Graph(id="price-chart"),

    # Interval actualizare automată
    dcc.Interval(id="interval-update", interval=30*1000, n_intervals=0)
])

# === CALLBACK STRATEGIE + SEMNAL LIVE ===
@app.callback(
    [Output("strategy-box", "children"),
     Output("live-signal", "children"),
     Output("price-chart", "figure")],
    [Input("interval-update", "n_intervals")]
)
def update_strategy_and_chart(n):
    strategy = load_strategy()
    if not strategy:
        return "⚠️ Nicio strategie optimă găsită. Rulează optimizatorul.", "❌", go.Figure()

    # Semnal live
    live_signal = get_live_signal(strategy)

    # Pregătim graficul prețului
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

    # Afisăm detalii strategie
    strategy_info = f"""
    RSI_Period: {strategy['RSI_Period']} | RSI_OB: {strategy['RSI_OB']} | RSI_OS: {strategy['RSI_OS']}  
    MACD_Fast: {strategy['MACD_Fast']} | MACD_Slow: {strategy['MACD_Slow']} | MACD_Signal: {strategy['MACD_Signal']}  
    Profit Estimat: {round(float(strategy['Profit']), 2)} USDT  
    Ultima Optimizare: {strategy['Updated']}
    """

    return strategy_info, live_signal, fig

# === RUN APP ===
if __name__ == "__main__":
    app.run(debug=True)
