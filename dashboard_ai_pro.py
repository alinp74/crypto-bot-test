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

# === DESCĂRCARE DATE ISTORICE ===
def get_historical(period="6 months ago UTC", interval="1h"):
    klines = client.get_historical_klines(SYMBOL, interval, period)
    df = pd.DataFrame(klines, columns=[
        "timestamp", "open", "high", "low", "close", "volume",
        "close_time", "qav", "num_trades", "tbbav", "tbqav", "ignore"
    ])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df["close"] = df["close"].astype(float)
    return df

# === FUNCȚIE STRATEGIE ===
def apply_strategy(df, strategy):
    df["rsi"] = ta.momentum.RSIIndicator(df["close"], window=int(strategy["RSI_Period"])).rsi()
    macd = ta.trend.MACD(
        df["close"],
        window_slow=int(strategy["MACD_Slow"]),
        window_fast=int(strategy["MACD_Fast"]),
        window_sign=int(strategy["MACD_Signal"])
    )
    df["macd"] = macd.macd()
    df["signal"] = macd.macd_signal()
    df.dropna(inplace=True)
    return df

# === RULEAZĂ SIMULAREA ===
def run_simulation(strategy, stop_loss, take_profit, period):
    df = get_historical(period=period, interval="1h")
    df = apply_strategy(df, strategy)

    trades = []
    capital = CAPITAL_INITIAL
    position = None
    entry_price = None

    for i in range(1, len(df)):
        price = df["close"].iloc[i]
        rsi = df["rsi"].iloc[i]
        macd_val = df["macd"].iloc[i]
        macd_sig = df["signal"].iloc[i]

        # Intrare LONG
        if position is None and rsi < float(strategy["RSI_OS"]) and macd_val > macd_sig:
            position = "LONG"
            entry_price = price

        elif position == "LONG":
            change = (price - entry_price) / entry_price * 100
            # Stop-loss activat
            if change <= -stop_loss:
                pnl = -CAPITAL_INITIAL * (stop_loss / 100)
                capital += pnl
                trades.append({"entry": entry_price, "exit": price, "pnl": pnl, "reason": "STOP LOSS"})
                position = None
            # Take-profit sau vânzare pe semnal
            elif change >= take_profit or (rsi > float(strategy["RSI_OB"]) and macd_val < macd_sig):
                pnl = CAPITAL_INITIAL * (change / 100)
                capital += pnl
                trades.append({"entry": entry_price, "exit": price, "pnl": pnl, "reason": "TAKE PROFIT"})
                position = None

    pnl_series = pd.Series([t["pnl"] for t in trades]).cumsum()
    return trades, capital, pnl_series

# === DASHBOARD ===
app = dash.Dash(__name__, suppress_callback_exceptions=True)
app.title = "AI Trading PRO Dashboard"

app.layout = html.Div([
    html.H1("🤖 AI Trading Dashboard PRO", style={'textAlign': 'center'}),

    dcc.Tabs([
        # === TAB PRINCIPAL ===
        dcc.Tab(label="Trading Live", children=[
            html.Div(id="strategy-info", style={'fontSize': 18, 'marginBottom': '15px'}),
            dcc.Graph(id="price-chart"),
            html.Div(id="wallet-balance", style={'fontSize': 18, 'marginTop': '15px'})
        ]),

        # === TAB SIMULATOR ===
        dcc.Tab(label="Simulator Scenarii", children=[
            html.H3("📊 Testează Strategia Ta", style={'textAlign': 'center'}),
            html.Div([
                html.Label("Perioadă Testare:"),
                dcc.Dropdown(
                    id="period",
                    options=[
                        {"label": "Ultimele 3 luni", "value": "3 months ago UTC"},
                        {"label": "Ultimele 6 luni", "value": "6 months ago UTC"},
                        {"label": "Ultimele 12 luni", "value": "12 months ago UTC"}
                    ],
                    value="6 months ago UTC"
                ),
                html.Label("Stop-Loss (%)"),
                dcc.Input(id="stop-loss", type="number", value=2, step=0.1),
                html.Label("Take-Profit (%)"),
                dcc.Input(id="take-profit", type="number", value=3, step=0.1),
                html.Button("Rulează Simulare", id="run-sim", n_clicks=0, style={'marginTop': '10px'})
            ], style={'width': '40%', 'margin': 'auto'}),

            html.Div(id="simulation-results", style={'fontSize': 18, 'marginTop': '20px'}),
            dcc.Graph(id="simulation-chart")
        ])
    ])
])

# === CALLBACK SIMULATOR ===
@app.callback(
    [Output("simulation-results", "children"),
     Output("simulation-chart", "figure")],
    [Input("run-sim", "n_clicks")],
    [State("stop-loss", "value"), State("take-profit", "value"), State("period", "value")]
)
def update_simulation(n, stop_loss, take_profit, period):
    if n == 0:
        return "", go.Figure()

    strategy = load_strategy()
    trades, final_capital, pnl_series = run_simulation(strategy, stop_loss, take_profit, period)

    total_trades = len(trades)
    wins = len([t for t in trades if t["pnl"] > 0])
    losses = total_trades - wins
    success_rate = round((wins / total_trades) * 100, 2) if total_trades > 0 else 0
    total_profit = round(final_capital - CAPITAL_INITIAL, 2)

    results_text = (
        f"📊 Rezultate Simulare\n"
        f"Tranzacții totale: {total_trades}\n"
        f"Câștigătoare: {wins} | Pierdute: {losses}\n"
        f"Rata succes: {success_rate}%\n"
        f"Profit total: {total_profit} USDT\n"
        f"Capital final: {round(final_capital, 2)} USDT"
    )

    fig = go.Figure()
    fig.add_trace(go.Scatter(y=pnl_series, mode="lines", name="Evoluție Capital"))
    fig.update_layout(title="📈 Evoluție Portofoliu", xaxis_title="Tranzacții", yaxis_title="Profit/Pierdere (USDT)")

    return results_text, fig

# === RUN APP ===
if __name__ == "__main__":
    app.run(debug=True)
