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

def export_table(table_name, file_name):
    try:
        df = pd.read_sql(f"SELECT * FROM {DB_SCHEMA}.{table_name} ORDER BY timestamp", engine)
        df.to_csv(file_name, index=False)
        print(f"✅ {table_name} exportat în {file_name} ({len(df)} rânduri)")
    except Exception as e:
        print(f"❌ Eroare export {table_name}: {e}")

if __name__ == "__main__":
    export_table("signals", "signals.csv")
    export_table("trades", "trades.csv")
    export_table("prices", "prices.csv")
