import pandas as pd
import warnings
import logging
from kraken_client import get_ohlc

# Configurare logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# Ignoră warningurile de tip FutureWarning (ex: fillna, rolling, freq)
warnings.filterwarnings("ignore", category=FutureWarning)


def semnal_tranzactionare(symbol: str, config: dict):
    """
    Generează semnal de tranzacționare (BUY, SELL, HOLD)
    pe baza RSI, MACD și volatilității.
    """

    # Obține date OHLC de la Kraken
    df = get_ohlc(symbol, interval=1, since=None)

    if df is None or df.empty:
        logger.warning(f"[strategie] Nu s-au putut obține date pentru {symbol}")
        return "HOLD"

    # Calcul RSI
    rsi_period = config.get("RSI_Period", 14)
    delta = df["close"].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(rsi_period).mean()
    avg_loss = loss.rolling(rsi_period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    df["RSI"] = rsi

    # Calcul MACD
    exp1 = df["close"].ewm(span=config.get("MACD_Fast", 12), adjust=False).mean()
    exp2 = df["close"].ewm(span=config.get("MACD_Slow", 26), adjust=False).mean()
    macd = exp1 - exp2
    signal = macd.ewm(span=config.get("MACD_Signal", 9), adjust=False).mean()
    df["MACD"] = macd
    df["Signal"] = signal

    # Volatilitate
    df["volatility"] = df["close"].pct_change().rolling(10).std()

    # Ultimele valori
    last_rsi = df["RSI"].iloc[-1]
    last_macd = df["MACD"].iloc[-1]
    last_signal = df["Signal"].iloc[-1]
    last_close = df["close"].iloc[-1]

    # Condiții semnal
    if last_rsi < config.get("RSI_OS", 30) and last_macd > last_signal:
        semnal = "BUY"
    elif last_rsi > config.get("RSI_OB", 70) and last_macd < last_signal:
        semnal = "SELL"
    else:
        semnal = "HOLD"

    # Log clar pentru semnal
    logger.info(f"[strategie] {symbol} | Preț={last_close:.2f} | RSI={last_rsi:.2f} | Semnal={semnal}")

    return semnal
