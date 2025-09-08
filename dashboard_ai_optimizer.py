import os
import json
import pandas as pd
import ta
from dotenv import load_dotenv
from binance.client import Client
import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
import plotly.graph_objs as go
from itertools import product
from datetime import datetime

# === CONFIG ===
load_dotenv()
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
SYMBOL = "BTCUSDT"
CAPITAL_INITIAL = 10000

client = Client(API_KEY, API_SECRET)
client.API_URL = "https://testnet.binance.vision/api"

# === ÎNCĂRCARE STRATEGIE ===
def load_strategy():
    if os.path.exists("strategy.json"):
        with open("strategy.json", "r") as f:
            return json.load(f)
    return None

# === DESCĂRCARE DATE ===
def get_historical(period="6 months ago UTC", interval="1h"):
    klines = client.get_historical_klines(SYMBOL, interval, period)
    df = pd.DataFrame(klines, columns=[
        "timestamp", "open", "high", "low", "close", "volume",
        "close_time", "qav", "num_trades", "tbbav", "tbqav", "ignore"
    ])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df["close"] = df["close"].astype(float)
    return df

# === STRATEGIE: RSI + MACD ===
def apply_strategy(df, rsi_period, rsi_ob, rsi_os, macd_fast, macd_slow, macd_signal):
    df["rsi"] = ta.momentum.RSIIndicator(df["close"], window=rsi_period).rsi()
    macd = ta.trend.MACD(df["close"], window_slow=macd_slow, window_fast=macd_fast, window_sign=macd_signal)
    df["macd"] = macd.macd()
    df["signal"] = macd.macd_signal()
    df.dropna(inplace=True)
    return df

# === SIMULARE STRATEGIE ===
def simulate(df, rsi_period, rsi_ob, rsi_os, macd_fast, macd_slow, macd_signal, stop_loss, take_profit):
    df = apply_strategy(df, rsi_period, rsi_ob, rsi_os, macd_fast, macd_slow, macd_signal)
    capital = CAPITAL_INITIAL
    position = None
    entry_price = None
    for i in range(1, len(df)):
        price = df["close"].iloc[i]
        rsi = df["rsi"].iloc[i]
        macd_val = df["macd"].iloc[i]
        macd_sig = df["signal"].iloc[i]
        # BUY
        if position is None and rsi < rsi_os and macd_val > macd_sig:
            position = "LONG"
            entry_price = price
        elif position == "LONG":
            change = (price - entry_price) / entry_price * 100
            # STOP-LOSS
            if change <= -stop_loss:
                capital += -CAPITAL_INITIAL * (stop_loss / 100)
                position = None
            # TAKE-PROFIT
            elif change >= take_profit or (rsi > rsi_ob and macd_val < macd_sig):
                capital += CAPITAL_INITIAL * (change / 100)
                position = None
    return capital

# === OPTIMIZARE AUTOMATĂ ===
def run_optimizer():
    df = get_historical()
    rsi_periods = [7, 14, 21]
    rsi_ob_levels = [65, 70, 75]
    rsi_os_levels = [25, 30, 35]
    macd_fast_vals = [8, 12]
    macd_slow_vals = [18, 26]
    macd_signal_vals = [5, 9]
    stop_losses = [1.5, 2.0, 3.0]
    take_profits = [2.0, 3.0, 5.0]
    best_profit = -999999
    best_config = None

    for rsi_period, rsi_ob, rsi_os, macd_fast, macd_slow, macd_signal, stop_loss, take_profit in product(
        rsi_periods, rsi_ob_levels, rsi_os_levels,
        macd_fast_vals, macd_slow_vals, macd_signal_vals,
        stop_losses, take_profits
    ):
        try:
            capital = simulate(df, rsi_period, rsi_ob, rsi_os, macd_fast, macd_slow, macd_signal, stop_loss, take_profit)
            profit = capital - CAPITAL_INITIAL
            if profit > best_profit:
                best_profit = profit
                best_config = {
                    "RSI_Period": rsi_period,
                    "RSI_OB": rsi_ob,
                    "RSI_OS": rsi_os,
                    "MACD_Fast": macd_fast,
                    "MACD_Slow": macd_slow,
                    "MACD_Signal": macd_signal,
                    "Stop_Loss": stop_loss,
                    "Take_Profit": take_profit,
                    "Profit": round(profit, 2)
                }
        except:
            continue

    if best_config:
        best_config["Updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open("strategy.json", "w") as f:
            json.dump(best_config, f, indent=4)
        return best_config
    return None

# === DASHBOARD ===
app = dash.Dash(__name__, suppress_callback_exceptions=True)
app.title = "AI Trading Dashboard + Optimizer"

app.layout = html.Div([
    html.H1("🤖 AI Trading Dashboard PRO", style={'textAlign': 'center'}),

    dcc.Tabs([
        # === TAB TRADING LIVE ===
        dcc.Tab(label="Trading Live", children=[
            html.Div(id="strategy-info", style={'fontSize': 18, 'marginBottom': '15px'}),
            dcc.Graph(id="price-chart")
        ]),

        # === TAB OPTIMIZATOR ===
        dcc.Tab(label="AI Optimizer", children=[
            html.H3("⚡ Optimizează Strategia Automat", style={'textAlign': 'center'}),
            html.Button("Rulează Optimizare", id="run-opt", n_clicks=0, style={'marginTop': '10px'}),
            html.Div(id="optimizer-status", style={'marginTop': '20px', 'fontSize': 18}),
            html.Div(id="optimizer-result", style={'marginTop': '20px', 'fontSize': 18})
        ])
    ])
])

# === CALLBACK PENTRU OPTIMIZATOR ===
@app.callback(
    [Output("optimizer-status", "children"),
     Output("optimizer-result", "children")],
    [Input("run-opt", "n_clicks")]
)
def update_optimizer(n_clicks):
    if n_clicks == 0:
        return "", ""
    return run_optimizer_status()

def run_optimizer_status():
    status_text = "🔄 Optimizarea rulează... poate dura câteva minute ⏳"
    best_strategy = run_optimizer()
    if best_strategy:
        result_text = (
            f"✅ Strategie optimă găsită!\n"
            f"RSI: {best_strategy['RSI_Period']} | OB: {best_strategy['RSI_OB']} | OS: {best_strategy['RSI_OS']}\n"
            f"MACD: {best_strategy['MACD_Fast']}/{best_strategy['MACD_Slow']}/{best_strategy['MACD_Signal']}\n"
            f"Stop-Loss: {best_strategy['Stop_Loss']}% | Take-Profit: {best_strategy['Take_Profit']}%\n"
            f"Profit Estimat: {best_strategy['Profit']} USDT"
        )
    else:
        result_text = "⚠️ Nicio strategie optimă găsită."
    return status_text, result_text

# === RUN ===
if __name__ == "__main__":
    app.run(debug=True)
