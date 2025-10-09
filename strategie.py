import pandas as pd
import numpy as np
from datetime import datetime
from kraken_client import k  # KrakenAPI din kraken_client

# Dezactivăm avertismentele Pandas
import warnings
warnings.filterwarnings("ignore", category=FutureWarning)

# Cache pentru ultima oră procesată
ultima_ora_semnal = {}

def calculeaza_RSI(prices, period=14):
    delta = prices.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

def calculeaza_MACD(prices, fast=12, slow=26, signal=9):
    exp1 = prices.ewm(span=fast, adjust=False).mean()
    exp2 = prices.ewm(span=slow, adjust=False).mean()
    macd = exp1 - exp2
    signal_line = macd.ewm(span=signal, adjust=False).mean()
    return macd, signal_line

def calculeaza_volatilitate(prices, perioada=14):
    return prices.pct_change().rolling(perioada).std().iloc[-1]

def calculeaza_semnal(pair, strategie):
    global ultima_ora_semnal
    try:
        # 📊 timeframe 1 oră
        ohlc, _ = k.get_ohlc_data(pair, interval=60, ascending=True)
        close_prices = ohlc['close']

        ultima_candela = ohlc.index[-1]
        ultima_ora = ultima_candela.replace(minute=0, second=0, microsecond=0)

        # ⚡ Dacă nu avem o candelă nouă, returnăm semnalul precedent
        if pair in ultima_ora_semnal and ultima_ora_semnal[pair]["ora"] == ultima_ora:
            prev = ultima_ora_semnal[pair]
            return prev["semnal"], prev["scor"], prev["volatilitate"]

        # 📈 RSI (perioadă 14, praguri mai sensibile)
        rsi = calculeaza_RSI(close_prices, strategie.get("RSI_Period", 14))
        rsi_curent = rsi.iloc[-1]

        # 📉 MACD (12,26,9)
        macd, signal_line = calculeaza_MACD(
            close_prices,
            strategie.get("MACD_Fast", 12),
            strategie.get("MACD_Slow", 26),
            strategie.get("MACD_Signal", 9)
        )
        macd_curent = macd.iloc[-1]
        signal_curent = signal_line.iloc[-1]

        # 🔄 Volatilitate
        volatilitate = calculeaza_volatilitate(close_prices)

        # 🧠 Praguri RSI relaxate (35/65)
        rsi_os = strategie.get("RSI_OS", 35)
        rsi_ob = strategie.get("RSI_OB", 65)

        # 📊 Condiții semnal echilibrate dar sensibile
        if (rsi_curent < rsi_os) and (macd_curent > signal_curent):
            semnal = "BUY"
        elif (rsi_curent > rsi_ob) and (macd_curent < signal_curent):
            semnal = "SELL"
        else:
            semnal = "HOLD"

        # 🧮 Scor în funcție de distanța RSI de 50
        scor = abs(rsi_curent - 50) / 50 * 100

        # 🕐 Salvăm pentru cache
        ultima_ora_semnal[pair] = {
            "ora": ultima_ora,
            "semnal": semnal,
            "scor": scor,
            "volatilitate": volatilitate
        }

        print(f"[{datetime.now()}] 🕐 Lumânare nouă detectată ({pair}) — RSI={rsi_curent:.2f}, MACD={macd_curent:.4f}, Signal={signal_curent:.4f} → {semnal}")

        return semnal, scor, volatilitate

    except Exception as e:
        print(f"[{datetime.now()}] ❌ Eroare în strategie: {e}")
        return "HOLD", 0, 0
