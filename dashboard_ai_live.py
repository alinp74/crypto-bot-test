import os
import json
import pandas as pd
import ta
import dash
import plotly.graph_objs as go
from dash import dcc, html
from dash.dependencies import Input, Output, State
from dotenv import load_dotenv
from binance.client import Client
from datetime import datetime
from threading import Thread
import time

# === CONFIG ===
load_dotenv()
API_KEY = os.getenv("API_KEY_MAINNET")
API_SECRET = os.getenv("API_SECRET_MAINNET")
SYMBOL = "BTCUSDT"
QUANTITY = 0.001
CAPITAL_INITIAL = 10000

client = Client(API_KEY, API_SECRET)

# === ÎNCĂRCARE STRATEGIE ===
def load_strategy():
    if os.path.exists("strategy.json"):
        with open("strategy.json", "r") as f:
            return json.load(f)
    return None

# === DESCĂRCARE PREȚURI LIVE ===
def get_live_price():
    ticker = client.get_symbol_ticker(symbol=SYMBOL)
    return float(ticker["price"])

# === DESCĂRCARE SOLD ===
def get_wallet_balance():
    account = client.get_account()
    balances = account["balances"]
    btc = [b for b in balances if b["asset"] == "BTC"][0]
    usdt = [b for b in balances if b["asset"] == "USDT"][0]
    return float(btc["free"]), float(usdt["free"])

# === SEMNALE STRATEGIE ===
def generate_signal(df, strategy):
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
    rsi = df["rsi"].iloc[-1]
    macd_val = df["macd"].iloc[-1]
    macd_sig = df["signal"].iloc[-1]
    if rsi < float(strategy["RSI_OS"]) and macd_val > macd_sig:
        return "BUY"
    elif rsi > float(strategy["RSI_OB"]) and macd_val < macd_sig:
        return "SELL"
    return "HOLD"

# === EXECUTĂ ORDER REAL ===
def execute_order(order_type, price):
    try:
        order = client.create_order(
            symbol=SYMBOL,
            side="BUY" if order_type == "BUY" else "SELL",
            type="MARKET",
            quantity=QUANTITY
        )
        save_trade(order_type, price)
        return order
    except Exception as e:
        print(f"❌ Eroare execuție: {e}")
        return None

# === SALVEAZĂ TRANZACȚIA ===
def save_trade(order_type, price):
    trade = {
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "type": order_type,
        "price": price,
        "quantity": QUANTITY
    }
    history = []
    if os.path.exists("trade_log.json"):
        with open("trade_log.json", "r") as f:
            history = json.load(f)
    history.append(trade)
    with open("trade_log.json", "w") as f:
        json.dump(history, f, indent=4)

# === BOT REAL ===
bot_running = False
def trading_bot():
    global bot_running
    strategy = load_strategy()
    while bot_running:
        try:
            klines = client.get_klines(symbol=SYMBOL, interval=Client.KLINE_INTERVAL_15MINUTE, limit=100)
            df = pd.DataFrame(klines, columns=[
                "timestamp","open","high","low","close","volume",
                "close_time","qav","num_trades","tbbav","tbqav","ignore"
            ])
            df["close"] = df["close"].astype(float)
            signal = generate_signal(df, strategy)
            last_price = df["close"].iloc[-1]
            if signal in ["BUY", "SELL"]:
                execute_order(signal, last_price)
            time.sleep(15)
        except Exception as e:
            print(f"❌ Eroare bot: {e}")
            time.sleep(10)

# === DASHBOARD ===
app = dash.Dash(__name__, suppress_callback_exceptions=True)
app.title = "AI Trading Live Dashboard"

app.layout = html.Div([
    html.H1("🤖 AI Trading Dashboard LIVE", style={'textAlign': 'center'}),
    html.Div(id="wallet-balance", style={'fontSize': 18, 'marginBottom': '20px'}),
    html.Button("Pornește Botul", id="start-bot", n_clicks=0, style={'backgroundColor':'green','color':'white','marginRight':'10px'}),
    html.Button("Oprește Botul", id="stop-bot", n_clicks=0, style={'backgroundColor':'red','color':'white'}),
    dcc.Interval(id="balance-interval", interval=5000, n_intervals=0),
    html.H3("📊 Tranzacții Live"),
    dcc.Graph(id="trade-graph"),
    html.Div(id="bot-status", style={'fontSize':18,'marginTop':'20px'})
])

# === CALLBACK BOT ===
@app.callback(
    Output("bot-status", "children"),
    [Input("start-bot", "n_clicks"), Input("stop-bot", "n_clicks")]
)
def update_bot(start, stop):
    global bot_running
    ctx = dash.callback_context
    if not ctx.triggered:
        return ""
    button_id = ctx.triggered[0]["prop_id"].split(".")[0]
    if button_id == "start-bot":
        if not bot_running:
            bot_running = True
            thread = Thread(target=trading_bot)
            thread.start()
            return "✅ Botul a pornit pe Mainnet."
    elif button_id == "stop-bot":
        bot_running = False
        return "🛑 Botul a fost oprit."
    return ""

# === CALLBACK WALLET + GRAFIC ===
@app.callback(
    [Output("wallet-balance", "children"), Output("trade-graph", "figure")],
    Input("balance-interval", "n_intervals")
)
def update_dashboard(n):
    btc, usdt = get_wallet_balance()
    balance_text = f"💰 Sold: {btc:.4f} BTC | {usdt:.2f} USDT"

    trades = []
    if os.path.exists("trade_log.json"):
        with open("trade_log.json", "r") as f:
            trades = json.load(f)

    if trades:
        df = pd.DataFrame(trades)
        fig = go.Figure()
        fig.add_trace(go.Scatter(y=df["price"], mode="lines+markers", name="Tranzacții"))
        fig.update_layout(title="📈 Istoric Tranzacții Live", xaxis_title="Timp", yaxis_title="Preț (USDT)")
    else:
        fig = go.Figure()

    return balance_text, fig

if __name__ == "__main__":
    app.run(debug=True)
