import os
import json
import pandas as pd
from dotenv import load_dotenv
from binance.client import Client
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
client.API_URL = "https://testnet.binance.vision/api"

# === DASHBOARD ===
app = dash.Dash(__name__)
app.title = "Crypto Trading Bot Dashboard"

app.layout = html.Div([
    html.H1("🤖 Dashboard Bot Tranzacționare BTC/USDT", style={'textAlign': 'center'}),

    # Status bot live
    html.Div(id="bot-status", style={'fontSize': 20, 'margin': '10px', 'color': '#1a73e8'}),

    # Soldul contului
    html.Div(id="wallet-balance", style={'fontSize': 18, 'margin': '10px'}),

    # Grafic BTC/USDT
    dcc.Graph(id="price-chart"),

    # Indicatori RSI și MACD
    dcc.Graph(id="indicators-chart"),

    # Istoric tranzacții bot
    html.H3("📜 Istoric Tranzacții Bot"),
    html.Div(id="trade-history"),

    # Interval refresh
    dcc.Interval(
        id="interval-update",
        interval=5 * 1000,  # refresh la 5 secunde
        n_intervals=0
    )
])

# === CALLBACK PENTRU UPDATE ===
@app.callback(
    [Output("bot-status", "children"),
     Output("wallet-balance", "children"),
     Output("price-chart", "figure"),
     Output("indicators-chart", "figure"),
     Output("trade-history", "children")],
    [Input("interval-update", "n_intervals")]
)
def update_dashboard(n):
    try:
        # === 1. Citim statusul botului ===
        if os.path.exists("bot_status.json"):
            with open("bot_status.json", "r") as f:
                bot_data = json.load(f)
            bot_status = f"📌 Status: {bot_data['status']} | Poziție: {bot_data['position']} | Profit: {bot_data['profit_loss']:.2f} USDT"
        else:
            bot_status = "Botul rulează, dar încă nu avem date disponibile."

        # === 2. Sold cont BTC + USDT ===
        account = client.get_account()
        balances = account["balances"]
        filtered_balances = [b for b in balances if b["asset"] in ["BTC", "USDT"]]
        wallet_info = [f"{b['asset']}: liber={b['free']} | blocat={b['locked']}" for b in filtered_balances]
        wallet_display = html.Ul([html.Li(item) for item in wallet_info])

        # === 3. Grafic BTC/USDT ===
        klines = client.get_klines(symbol=SYMBOL, interval=Client.KLINE_INTERVAL_1MINUTE, limit=40)
        df = pd.DataFrame(klines, columns=[
            "timestamp", "open", "high", "low", "close", "volume",
            "close_time", "qav", "num_trades", "tbbav", "tbqav", "ignore"
        ])
        df["close"] = df["close"].astype(float)
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")

        fig_price = go.Figure(data=[
            go.Candlestick(
                x=df["timestamp"],
                open=df["open"],
                high=df["high"],
                low=df["low"],
                close=df["close"],
                name="BTC/USDT"
            )
        ])
        fig_price.update_layout(title="📈 Preț BTC/USDT", xaxis_rangeslider_visible=False)

        # === 4. Grafic RSI + MACD ===
        df["rsi"] = pd.Series(bot_data["rsi"] for _ in range(len(df)))
        df["macd"] = pd.Series(bot_data["macd"] for _ in range(len(df)))
        df["signal"] = pd.Series(bot_data["signal"] for _ in range(len(df)))

        fig_indicators = go.Figure()
        fig_indicators.add_trace(go.Scatter(x=df["timestamp"], y=df["rsi"], mode="lines", name="RSI"))
        fig_indicators.add_trace(go.Scatter(x=df["timestamp"], y=df["macd"], mode="lines", name="MACD"))
        fig_indicators.add_trace(go.Scatter(x=df["timestamp"], y=df["signal"], mode="lines", name="Signal"))
        fig_indicators.update_layout(title="📊 Indicatori RSI & MACD")

        # === 5. Istoric tranzacții ===
        trades = client.get_my_trades(symbol=SYMBOL)
        trades_sorted = sorted(trades, key=lambda x: x["time"], reverse=True)
        trade_history = []
        for t in trades_sorted[:10]:
            side = "CUMPĂRARE" if t["isBuyer"] else "VÂNZARE"
            trade_history.append(f"{side} | Cantitate: {t['qty']} BTC | Preț: {t['price']} USDT")
        trade_display = html.Ul([html.Li(item) for item in trade_history])

        return bot_status, wallet_display, fig_price, fig_indicators, trade_display

    except Exception as e:
        return (f"❌ Eroare: {e}", html.Div(""), go.Figure(), go.Figure(), html.Div(""))

# === RUN SERVER ===
if __name__ == "__main__":
    app.run(debug=True)
