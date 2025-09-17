import os
import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv

# încarcă variabilele din .env (Kraken + DB)
load_dotenv()

db_url = os.getenv("DATABASE_URL")
if db_url and db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

DB_SCHEMA = os.getenv("DB_SCHEMA", "public")
engine = create_engine(db_url)

def load_table(table_name):
    return pd.read_sql(
        f"SELECT * FROM {DB_SCHEMA}.{table_name} ORDER BY timestamp",
        engine
    )

if __name__ == "__main__":
    try:
        print("📥 Citim datele din Postgres...")
        df_prices = load_table("prices")
        df_signals = load_table("signals")
        df_trades = load_table("trades")

        print(f"✅ prices: {len(df_prices)} rânduri")
        print(f"✅ signals: {len(df_signals)} rânduri")
        print(f"✅ trades: {len(df_trades)} rânduri")

        # merge signals cu prices (pe symbol + cel mai apropiat timestamp)
        df = pd.merge_asof(
            df_prices.sort_values("timestamp"),
            df_signals.sort_values("timestamp"),
            on="timestamp",
            by="symbol",
            direction="backward",
            suffixes=("_price", "_signal")
        )

        # adaugăm și trades (pe symbol + timestamp apropiat)
        df = pd.merge_asof(
            df.sort_values("timestamp"),
            df_trades.sort_values("timestamp"),
            on="timestamp",
            by="symbol",
            direction="backward",
            suffixes=("", "_trade")
        )

        # salvăm dataset final
        output_file = "ai_dataset.csv"
        df.to_csv(output_file, index=False)
        print(f"📊 Dataset AI exportat în {output_file} ({len(df)} rânduri)")

    except Exception as e:
        print(f"❌ Eroare la export: {e}")
