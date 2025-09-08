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

# === CONFIG ===
load_dotenv()
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
SYMBOL = "BTCUSDT"

# Folosim date reale pentru backtest, chiar dacă botul rulează pe testnet
client = Client(API_KEY, API_SECRET)
client.API_URL = "https://api.binance.com/api"

# === DASHBOARD ===
app = dash.Dash(__name__)
app.title = "Crypto Bot - Dashboard Profesional v2"

app.layout = html.Div([
    html.H1("🤖 Dashboard Bot Trading BTC/USDT", style={'textAlign': 'center'}),
    dcc.Tabs(id="tabs", value="tab-live", children=[
        dcc.Tab(label="📈 LIVE Trading", value="tab-live"),
        dcc.Tab(label="🧠 Backtesting", value="tab-backtest")
    ]),
    html.Div(id="tabs-content")
])

# === TAB LIVE TRADING ===
def live_tab():
    return html.Div([
        html.H3("📌 Status Bot"),
        html.Div(id="bot-status", style={'fontSize': 20, 'color': '#1a73e8'}),
        html.H3("💰 Sold Cont (BTC + USDT)"),
        html.Div(id="wallet-balance", style={'fontSize': 18}),
        dcc.Graph(id="price-chart"),
        dcc.Graph(id="indicators-chart"),
        html.H3("📜 Istoric Tranzacții Bot"),
        html.Div(id="trade-history"),
        dcc.Interval(id="interval-live", interval=5*1000, n_intervals=0)
    ])

# === TAB BACKTEST ===
def backtest_tab():
    return html.Div([
        html.H3("🧠 Backtesting Strategie RSI + MACD"),
        html.Div([
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
            html.Label("Perioadă (ex: 90 days ago UTC):"),
            dcc.Input(id="period", type="text", value="90 days ago UTC"),
            html.Label("RSI Overbought:"),
            dcc.Input(id="rsi-overbought", type="number", value=70),
            html.Label("RSI Oversold:"),
            dcc.Input(id="rsi-oversold", type="number", value=30),
            html.Label("MACD Fast:"),
            dcc.Input(id="macd-fast", type="number", value=12),
            html.Label("MACD Slow:"),
            dcc.Input(id="macd-slow", type="number", value=26),
            html.Label("MACD Signal:"),
            dcc.Input(id="macd-signal", type="number", value=9),
            html.Button("🚀 Rulează Backtest", id="run-backtest", n_clicks=0)
        ], style={"display": "grid", "gridTemplateColumns": "repeat(3, 1fr)", "gap": "10px"}),

        html.Div(id="backtest-results", style={"marginTop": "20px"}),
        dcc.Graph(id="backtest-chart")
    ])

# === CONTINUT TABURI ===
@app.callback(Output("tabs-content", "children"), [Input("tabs", "value")])
def render_tab(tab):
    if tab == "tab-live":
        return live_tab()
    elif tab == "tab-backtest":
        return backtest_tab()

# === CALLBACK LIVE ===
@app.callback(
    [Output("bot-status", "children"),
     Output("wallet-balance", "children"),
     Output("price-chart", "figure"),
     Output("indicators-chart", "figure"),
     Output("trade-history", "children")],
    [Input("interval-live", "n_intervals")]
)
def update_live_tab(n):
    bot_status = "⚠️ Botul rulează, dar nu avem date încă."
    rsi = macd = signal = None

    # Status Bot
    try:
        if os.path.exists("bot_status.json"):
            with open("bot_status.json", "r") as f:
                bot_data = json.load(f)
            bot_status = (
                f"{bot_data['status']} | Preț: {bot_data['price']:.2f} USDT | "
                f"Poziție: {bot_data['position']} | Profit: {bot_data['profit_loss']:.2f} USDT"
            )
            rsi = bot_data["rsi"]
            macd = bot_data["macd"]
            signal = bot_data["signal"]
    except:
        pass

    # Sold cont
    try:
        account = client.get_account()
        balances = account["balances"]
        filtered = [b for b in balances if b["asset"] in ["BTC", "USDT"]]
        wallet_display = html.Ul([html.Li(f"{b['asset']}: liber={b['free']} | blocat={b['locked']}") for b in filtered])
    except:
        wallet_display = "❌ Eroare la citirea soldului"

    # Grafic preț live
    fig_price = go.Figure()
    try:
        klines = client.get_klines(symbol=SYMBOL, interval=Client.KLINE_INTERVAL_1MINUTE, limit=40)
        df = pd.DataFrame(klines, columns=[
            "timestamp", "open", "high", "low", "close", "volume",
            "close_time", "qav", "num_trades", "tbbav", "tbqav", "ignore"
        ])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df["close"] = df["close"].astype(float)
        df["open"] = df["open"].astype(float)
        df["high"] = df["high"].astype(float)
        df["low"] = df["low"].astype(float)

        fig_price = go.Figure(data=[go.Candlestick(
            x=df["timestamp"], open=df["open"], high=df["high"], low=df["low"], close=df["close"]
        )])
        fig_price.update_layout(title="📈 Preț BTC/USDT", xaxis_rangeslider_visible=False)
    except:
        fig_price.update_layout(title="Eroare grafic preț")

    # Grafic indicatori
    fig_indicators = go.Figure()
    if rsi is not None and macd is not None and signal is not None:
        fig_indicators.add_trace(go.Scatter(x=df["timestamp"], y=[rsi]*len(df), mode="lines", name="RSI"))
        fig_indicators.add_trace(go.Scatter(x=df["timestamp"], y=[macd]*len(df), mode="lines", name="MACD"))
        fig_indicators.add_trace(go.Scatter(x=df["timestamp"], y=[signal]*len(df), mode="lines", name="Signal"))
        fig_indicators.update_layout(title="📊 Indicatori RSI & MACD")

    # Istoric tranzacții
    try:
        trades = client.get_my_trades(symbol=SYMBOL)
        trades_sorted = sorted(trades, key=lambda x: x["time"], reverse=True)
        trade_info = [
            f"{'CUMPĂRARE' if t['isBuyer'] else 'VÂNZARE'} | Cantitate: {t['qty']} BTC | Preț: {t['price']} USDT"
            for t in trades_sorted[:10]
        ]
        trade_display = html.Ul([html.Li(item) for item in trade_info])
    except:
        trade_display = "⚠️ Nicio tranzacție încă"

    return bot_status, wallet_display, fig_price, fig_indicators, trade_display

# === CALLBACK BACKTEST ===
@app.callback(
    [Output("backtest-results", "children"),
     Output("backtest-chart", "figure")],
    [Input("run-backtest", "n_clicks")],
    [State("interval", "value"),
     State("period", "value"),
     State("rsi-overbought", "value"),
     State("rsi-oversold", "value"),
     State("macd-fast", "value"),
     State("macd-slow", "value"),
     State("macd-signal", "value")]
)
def run_backtest(n_clicks, interval, period, rsi_overbought, rsi_oversold, macd_fast, macd_slow, macd_signal):
    if n_clicks == 0:
        return "", go.Figure()

    # Descărcare date
    klines = client.get_historical_klines(SYMBOL, interval, period)
    df = pd.DataFrame(klines, columns=[
        "timestamp", "open", "high", "low", "close", "volume",
        "close_time", "qav", "num_trades", "tbbav", "tbqav", "ignore"
    ])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df["close"] = df["close"].astype(float)

    # Indicatori tehnici
    df["rsi"] = ta.momentum.RSIIndicator(df["close"], window=14).rsi()
    macd = ta.trend.MACD(df["close"], window_slow=macd_slow, window_fast=macd_fast, window_sign=macd_signal)
    df["macd"] = macd.macd()
    df["signal"] = macd.macd_signal()
    df = df.dropna()

    # Backtest simplu
    balance = 10000
    position = None
    entry_price = 0
    trade_history = []
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
                trade_history.append(("BUY", df["timestamp"].iloc[i], price))
        elif position == "LONG":
            if rsi > rsi_overbought or macd_val < signal_val:
                pnl = price - entry_price
                balance += pnl
                if pnl > 0:
                    profit_trades += 1
                else:
                    loss_trades += 1
                trade_history.append(("SELL", df["timestamp"].iloc[i], price))
                position = None

    profit_total = balance - 10000
    total_trades = profit_trades + loss_trades
    success_rate = (profit_trades / total_trades * 100) if total_trades > 0 else 0

    results = html.Div([
        html.H4("📊 Rezultate Backtest"),
        html.P(f"Tranzacții totale: {total_trades}"),
        html.P(f"Tranzacții profitabile: {profit_trades}"),
        html.P(f"Tranzacții pierdute: {loss_trades}"),
        html.P(f"Rata de succes: {success_rate:.2f}%"),
        html.P(f"Profit total: {profit_total:.2f} USDT"),
        html.P(f"Sold final: {balance:.2f} USDT")
    ])

    # Grafic Backtest
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["timestamp"], y=df["close"], mode="lines", name="Preț BTC/USDT"))
    for trade in trade_history:
        if trade[0] == "BUY":
            fig.add_trace(go.Scatter(x=[trade[1]], y=[trade[2]], mode="markers", name="BUY",
                                     marker=dict(color="green", size=10, symbol="triangle-up")))
        else:
            fig.add_trace(go.Scatter(x=[trade[1]], y=[trade[2]], mode="markers", name="SELL",
                                     marker=dict(color="red", size=10, symbol="triangle-down")))
    fig.update_layout(title="Backtesting RSI + MACD")
    return results, fig

# === RUN ===
if __name__ == "__main__":
    app.run(debug=True)
