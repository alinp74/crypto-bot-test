import os
import json
import time
import pandas as pd
import plotly.graph_objs as go
from dotenv import load_dotenv
from binance.client import Client
from dash import Dash, dcc, html, ctx
from dash.dependencies import Input, Output
from threading import Thread
from ai_risk_manager import manage_risk
from ai_auto_trader_real import generate_signal, get_latest_data, load_strategy, execute_order, save_trade

# === CONFIG ===
load_dotenv()
API_KEY = os.getenv("API_KEY_MAINNET")
API_SECRET = os.getenv("API_SECRET_MAINNET")
SYMBOL = "BTCUSDT"

client = Client(API_KEY, API_SECRET)

bot_running = False
strategy = load_strategy()

# === BOT REAL ===
def trading_bot():
    global bot_running, strategy
    while bot_running:
        try:
            # Descărcăm date live
            df = get_latest_data()
            signal = generate_signal(df, strategy)
            last_price = df["close"].iloc[-1]

            # Verificăm riscul
            risk = manage_risk()
            print(f"📊 RiskScore={risk['RiskScore']} | Volatilitate={risk['Volatilitate']} | DimPoz={risk['DimensiunePozitieBTC']} BTC")

            # Dacă riscul e prea mare, nu intrăm în tranzacție
            if not risk["Tranzactioneaza"]:
                print("⚠️ Tranzacție refuzată: risc prea mare sau daily drawdown depășit.")
                time.sleep(15)
                continue

            # Executăm ordinele doar dacă avem semnal
            if signal in ["BUY", "SELL"]:
                quantity = risk["DimensiunePozitieBTC"]
                order = execute_order(signal, last_price, quantity)
                if order:
                    save_trade(signal, last_price, quantity=quantity)
            else:
                print(f"⏳ Fără semnal clar. Ultimul preț: {last_price}")

            time.sleep(15)

        except Exception as e:
            print(f"❌ Eroare bot: {e}")
            time.sleep(10)

# === DASHBOARD ===
app = Dash(__name__)
app.title = "AI Trading Dashboard PRO"

app.layout = html.Div([
    html.H1("🤖 AI Trading Dashboard PRO", style={'textAlign': 'center'}),

    html.Div(id="wallet-balance", style={'fontSize': 18, 'marginBottom': '20px'}),

    html.Div([
        html.Button("Pornește Botul", id="start-bot", n_clicks=0,
                    style={'backgroundColor':'green','color':'white','marginRight':'10px'}),
        html.Button("Oprește Botul", id="stop-bot", n_clicks=0,
                    style={'backgroundColor':'red','color':'white'}),
    ], style={'textAlign': 'center', 'marginBottom': '20px'}),

    html.H3("📊 Tranzacții Live"),
    dcc.Graph(id="trade-graph"),

    html.H3("📈 Evoluție Preț BTC"),
    dcc.Graph(id="price-graph"),

    html.Div(id="bot-status", style={'fontSize':18,'marginTop':'20px'}),
    dcc.Interval(id="interval-refresh", interval=5000, n_intervals=0)
])

# === CALLBACK PORNIRE / OPRIRE BOT ===
@app.callback(
    Output("bot-status", "children"),
    [Input("start-bot", "n_clicks"), Input("stop-bot", "n_clicks")]
)
def control_bot(start_clicks, stop_clicks):
    global bot_running

    # Identificăm ce buton a declanșat evenimentul
    triggered_id = ctx.triggered_id

    if triggered_id == "start-bot" and not bot_running:
        bot_running = True
        from threading import Thread
        thread = Thread(target=trading_bot)
        thread.start()
        return "✅ Botul rulează pe MAINNET."
    elif triggered_id == "stop-bot":
        bot_running = False
        return "🛑 Botul a fost oprit."

    return "Bot inactiv."

    if button_id == "start-bot" and not bot_running:
        bot_running = True
        thread = Thread(target=trading_bot)
        thread.start()
        return "✅ Botul rulează pe MAINNET."
    elif button_id == "stop-bot":
        bot_running = False
        return "🛑 Botul a fost oprit."
    return "Bot inactiv."

# === CALLBACK SOLD + GRAFICE ===
@app.callback(
    [Output("wallet-balance", "children"),
     Output("trade-graph", "figure"),
     Output("price-graph", "figure")],
    [Input("interval-refresh", "n_intervals")]
)
def update_dashboard(n):
    # Sold actualizat
    balances = client.get_account()["balances"]
    btc_balance = float([b for b in balances if b["asset"]=="BTC"][0]["free"])
    usdt_balance = float([b for b in balances if b["asset"]=="USDT"][0]["free"])
    balance_text = f"💰 Sold: {btc_balance:.4f} BTC | {usdt_balance:.2f} USDT"

    # Tranzacții salvate
    trades = []
    if os.path.exists("trade_log.json"):
        with open("trade_log.json", "r") as f:
            trades = json.load(f)

    trade_fig = go.Figure()
    if trades:
        df = pd.DataFrame(trades)
        trade_fig.add_trace(go.Scatter(y=df["entry_price"], mode="lines+markers", name="Tranzacții"))
        trade_fig.update_layout(title="📊 Istoric Tranzacții", xaxis_title="Timp", yaxis_title="Preț")

    # Evoluția prețului BTC
    df_price = get_latest_data()
    price_fig = go.Figure()
    price_fig.add_trace(go.Scatter(x=df_price["timestamp"], y=df_price["close"], mode="lines", name="Preț BTC"))
    price_fig.update_layout(title="📈 Evoluția Prețului BTC", xaxis_title="Timp", yaxis_title="Preț (USDT)")

    return balance_text, trade_fig, price_fig

if __name__ == "__main__":
    app.run(debug=True)

