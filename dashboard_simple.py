import os
import json
from dotenv import load_dotenv
from binance.client import Client
import dash
from dash import html
from dash.dependencies import Input, Output

# === CONFIG ===
load_dotenv()
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")

client = Client(API_KEY, API_SECRET)
client.API_URL = "https://testnet.binance.vision/api"

# === DASHBOARD ===
app = dash.Dash(__name__)
app.title = "Crypto Bot - Dashboard Simplificat"

app.layout = html.Div([
    html.H1("🤖 Dashboard Bot Tranzacționare BTC/USDT", style={'textAlign': 'center'}),

    html.H3("📌 Status Bot"),
    html.Div(id="bot-status", style={'fontSize': 20, 'color': '#1a73e8', 'marginBottom': '20px'}),

    html.H3("💰 Sold Cont (BTC + USDT)"),
    html.Div(id="wallet-balance", style={'fontSize': 18, 'marginBottom': '20px'}),

    # Refresh la fiecare 5 secunde
    dash.dcc.Interval(
        id="interval-update",
        interval=5 * 1000,  # 5 secunde
        n_intervals=0
    )
])

# === CALLBACK PENTRU UPDATE ===
@app.callback(
    [Output("bot-status", "children"),
     Output("wallet-balance", "children")],
    [Input("interval-update", "n_intervals")]
)
def update_dashboard(n):
    # === 1. Citim statusul botului ===
    bot_status = "⚠️ Botul rulează, dar nu avem date încă."
    if os.path.exists("bot_status.json"):
        try:
            with open("bot_status.json", "r") as f:
                bot_data = json.load(f)
            bot_status = (
                f"📌 {bot_data['status']} | "
                f"Preț: {bot_data['price']:.2f} USDT | "
                f"Poziție: {bot_data['position']} | "
                f"Profit: {bot_data['profit_loss']:.2f} USDT"
            )
        except Exception as e:
            bot_status = f"❌ Eroare la citirea fișierului: {e}"

    # === 2. Sold BTC + USDT ===
    try:
        account = client.get_account()
        balances = account["balances"]
        filtered = [b for b in balances if b["asset"] in ["BTC", "USDT"]]
        wallet_info = [f"{b['asset']}: liber={b['free']} | blocat={b['locked']}" for b in filtered]
        wallet_display = html.Ul([html.Li(item) for item in wallet_info])
    except Exception as e:
        wallet_display = f"❌ Eroare la citirea soldului: {e}"

    return bot_status, wallet_display

# === RUN SERVER ===
if __name__ == "__main__":
    app.run(debug=True)
