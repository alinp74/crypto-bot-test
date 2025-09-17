import psycopg2
import os
import pandas as pd

def check_db():
    try:
        conn = psycopg2.connect(os.getenv("DATABASE_URL"))
        print("✅ Conectat la baza de date\n")

        # ultimele 5 semnale
        signals_query = """
            SELECT timestamp, symbol, signal, price, risk_score, volatility
            FROM signals
            ORDER BY id DESC
            LIMIT 5
        """
        signals_df = pd.read_sql(signals_query, conn)
        print("📊 Ultimele 5 semnale:")
        print(signals_df.to_string(index=False))
        print("\n")

        # ultimele 5 tranzacții
        trades_query = """
            SELECT timestamp, symbol, action, quantity, price, profit_pct, status
            FROM trades
            ORDER BY id DESC
            LIMIT 5
        """
        trades_df = pd.read_sql(trades_query, conn)
        print("💰 Ultimele 5 tranzacții:")
        print(trades_df.to_string(index=False))

        conn.close()

    except Exception as e:
        print(f"❌ Eroare la citirea DB: {e}")


if __name__ == "__main__":
    check_db()
