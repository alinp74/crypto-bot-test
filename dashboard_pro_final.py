import os
import json
import pandas as pd
from dotenv import load_dotenv
from binance.client import Client
import ta
import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
import plotly.graph_objs as go
from itertools import product

# === CONFIG ===
load_dotenv()
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
SYMBOL = "BTCUSDT"

client = Client(API_KEY, API_SECRET)
client.API_URL = "https://api.binance.com/api"

# === FUNCȚIE DESCĂRCARE DATE ===
def get_historical(interval="15m", period="180 days ago UTC"):
    klines = client.get_historical_klines(SYMBOL, interval, period)
    df = pd.DataFrame(klines, columns=[
        "timestamp", "open", "high", "low", "close", "volume",
        "close_time", "qav", "num_trades", "tbbav", "tbqav", "ignore"
    ])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df["close"] = df["close"].astype(float)
    return df

# === FUNCȚIE STRATEGIE RSI + MACD ===
def run_strategy(df, rsi_period, rsi_overbought, rsi_oversold, macd_fast, macd_slow, macd_signal):
    df["rsi"] = ta.momentum.RSIIndicator(df["close"], window=rsi_period).rsi()
    macd = ta.trend.MACD(df["close"], window_slow=macd_slow, window_fast=macd_fast, window_sign=macd_signal)
    df["macd"] = macd.macd()
    df["signal"] = macd.macd_signal()
    df = df.dropna()

    balance = 10000
    position = None
    entry_price = 0
    profit_trades = loss_trades = 0

    for i in range(len(df)):
        price = df["close"].iloc[i]
        rsi = df["rsi"].iloc[i]
        macd_val = df["macd"].iloc[i]
        signal_val = df["signal"].iloc[i]

        if position is None:
            if rsi < rsi_oversold and macd_val > signal_val:
                position = "LONG"
                entry_price = price
        elif position == "LONG":
            if rsi > rsi_overbought or macd_val < signal_val:
                pnl = price - entry_price
                balance += pnl
                if pnl > 0:
                    profit_trades += 1
                else:
                    loss_trades += 1
                position = None

    total_trades = profit_trades + loss_trades
    success_rate = (profit_trades / total_trades * 100) if total_trades > 0 else 0
    profit_total = balance - 10000
    return profit_total, success_rate, total_trades

# === FUNCȚIE OPTIMIZARE STRATEGII ===
def optimizer(df):
    rsi_periods = [7, 14]
    rsi_overboughts = [65, 70, 75]
    rsi_oversolds = [25, 30, 35]
    macd_fasts = [8, 12]
    macd_slows = [20, 26]
    macd_signals = [5, 9]

    results = []
    for rsi_p, rsi_ob, rsi_os, mf, ms, msig in product(
        rsi_periods, rsi_overboughts, rsi_oversolds, macd_fasts, macd_slows, macd_signals
    ):
        profit, success_rate, total_trades = run_strategy(df.copy(), rsi_p, rsi_ob, rsi_os, mf, ms, msig)
        results.append({
            "RSI_Period": rsi_p,
            "RSI_OB": rsi_ob,
            "RSI_OS": rsi_os,
            "MACD_Fast": mf,
            "MACD_Slow": ms,
            "MACD_Signal": msig,
            "Profit": profit,
            "Success_Rate": success_rate,
            "Total_Trades": total_trades
        })

    df_results = pd.DataFrame(results)
    df_results = df_results.sort_values(by="Profit", ascending=False)
    return df_results

# === DASHBOARD ===
app = dash.Dash(__name__)
app.title = "Crypto Bot - Dashboard Final"

app.layout = html.Div([
    html.H1("🤖 Dashboard Trading + Optimizator Strategii", style={'textAlign': 'center'}),
    dcc.Tabs(id="tabs", value="tab-live", children=[
        dcc.Tab(label="📈 LIVE Trading", value="tab-live"),
        dcc.Tab(label="🧠 Backtesting", value="tab-backtest"),
        dcc.Tab(label="🚀 Optimizator", value="tab-optimizer")
    ]),
    html.Div(id="tabs-content")
])

# === TABURI ===
@app.callback(Output("tabs-content", "children"), [Input("tabs", "value")])
def render_tab(tab):
    if tab == "tab-live":
        return html.Div([
            html.H3("📌 Status Bot"),
            html.Div(id="bot-status", style={'fontSize': 20}),
            html.H3("💰 Sold Cont (BTC + USDT)"),
            html.Div(id="wallet-balance", style={'fontSize': 18}),
            dcc.Graph(id="price-chart"),
            dcc.Graph(id="indicators-chart"),
            html.H3("📜 Istoric Tranzacții Bot"),
            html.Div(id="trade-history"),
            dcc.Interval(id="interval-live", interval=5*1000, n_intervals=0)
        ])
    elif tab == "tab-backtest":
        return html.Div([
            html.H3("🧠 Backtesting Strategie RSI + MACD"),
            html.Label("Interval:"),
            dcc.Dropdown(
                id="interval",
                options=[
                    {"label": "15 minute", "value": Client.KLINE_INTERVAL_15MINUTE},
                    {"label": "1 oră", "value": Client.KLINE_INTERVAL_1HOUR},
                    {"label": "4 ore", "value": Client.KLINE_INTERVAL_4HOUR},
                    {"label": "1 zi", "value": Client.KLINE_INTERVAL_1DAY}
                ],
                value=Client.KLINE_INTERVAL_15MINUTE
            ),
            html.Label("Perioadă:"),
            dcc.Input(id="period", type="text", value="90 days ago UTC"),
            html.Label("RSI Overbought:"), dcc.Input(id="rsi-overbought", type="number", value=70),
            html.Label("RSI Oversold:"), dcc.Input(id="rsi-oversold", type="number", value=30),
            html.Label("MACD Fast:"), dcc.Input(id="macd-fast", type="number", value=12),
            html.Label("MACD Slow:"), dcc.Input(id="macd-slow", type="number", value=26),
            html.Label("MACD Signal:"), dcc.Input(id="macd-signal", type="number", value=9),
            html.Button("🚀 Rulează Backtest", id="run-backtest", n_clicks=0),
            html.Div(id="backtest-results"),
            dcc.Graph(id="backtest-chart")
        ])
    elif tab == "tab-optimizer":
        return html.Div([
            html.H3("🚀 Optimizator Automat Strategii RSI + MACD"),
            html.Label("Interval date istorice:"),
            dcc.Dropdown(
                id="opt-interval",
                options=[
                    {"label": "15 minute", "value": Client.KLINE_INTERVAL_15MINUTE},
                    {"label": "1 oră", "value": Client.KLINE_INTERVAL_1HOUR}
                ],
                value=Client.KLINE_INTERVAL_15MINUTE
            ),
            html.Label("Perioadă testare:"),
            dcc.Input(id="opt-period", type="text", value="365 days ago UTC"),
            html.Button("🔍 Rulează Optimizator", id="run-optimizer", n_clicks=0),
            html.Div(id="optimizer-results")
        ])

# === CALLBACK OPTIMIZATOR ===
@app.callback(
    Output("optimizer-results", "children"),
    [Input("run-optimizer", "n_clicks")],
    [State("opt-interval", "value"),
     State("opt-period", "value")]
)
def run_optimizer(n_clicks, interval, period):
    if n_clicks == 0:
        return ""
    df = get_historical(interval=interval, period=period)
    results = optimizer(df)
    results.to_csv("optimizer_results.csv", index=False)
    top10 = results.head(10)
    return html.Div([
        html.H4("📊 TOP 10 Strategii Profitabile"),
        html.Pre(top10.to_string(index=False)),
        html.P("💾 Rezultatele complete sunt salvate în: optimizer_results.csv")
    ])

# === RUN ===
if __name__ == "__main__":
    app.run(debug=True)
