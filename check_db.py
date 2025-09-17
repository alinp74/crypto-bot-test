import os
import psycopg2
import pandas as pd
from dotenv import load_dotenv

# încarcă variabilele din .env
load_dotenv()

db_url = os.getenv("DATABASE_URL")
if db_url and db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

DB_SCHEMA = os.getenv("DB_SCHEMA", "public")

try:
    conn = psycopg2.connect(db_url)

    print("📊 Ultimele semnale:")
    df_signals = pd.read_sql(
        f"SELECT * FROM {DB_SCHEMA}.signals ORDER BY timestamp DESC LIMIT 10", conn
    )
    print(df_signals)

    print("\n📊 Ultimele tranzacții:")
    df_trades = pd.read_sql(
        f"SELECT * FROM {DB_SCHEMA}.trades ORDER BY timestamp DESC LIMIT 10", conn
    )
    print(df_trades)

    conn.close()
except Exception as e:
    print(f"❌ Eroare la citirea DB: {e}")
