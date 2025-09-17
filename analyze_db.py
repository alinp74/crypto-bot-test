import psycopg2
import os
import pandas as pd

def analyze_db():
    try:
        conn = psycopg2.connect(os.getenv("DATABASE_URL"))
        print("✅ Conectat la baza de date\n")

        # === Profit total ===
        profit_query = """
            SELECT COALESCE(SUM(profit_pct), 0) as total_profit
            FROM trades
            WHERE action LIKE 'SELL%'
              AND status = 'EXECUTED'
        """
        profit_df = pd.read_sql(profit_query, conn)
        total_profit = profit_df['total_profit'][0]
        print(f"💰 Profit total acumulat: {total_profit:.2f}%\n")

        # === Rata de succes ===
        success_query = """
            SELECT COUNT(*) FILTER (WHERE profit_pct > 0) as wins,
                   COUNT(*) FILTER (WHERE profit_pct <= 0) as losses
            FROM trades
            WHERE action LIKE 'SELL%'
              AND status = 'EXECUTED'
        """
        success_df = pd.read_sql(success_query, conn)
        wins, losses = success_df['wins'][0], success_df['losses'][0]
        total = wins + losses
        winrate = (wins / total * 100) if total > 0 else 0
        print(f"📈 Rata de succes: {wins}/{total} ({winrate:.2f}%)\n")

        # === Distribuția semnalelor per monedă ===
        signals_query = """
            SELECT symbol, signal, COUNT(*) as cnt
            FROM signals
            GROUP BY symbol, signal
            ORDER BY symbol, signal
        """
        signals_df = pd.read_sql(signals_query, conn)
        print("📊 Distribuția semnalelor:")
        print(signals_df.pivot(index="symbol", columns="signal", values="cnt").fillna(0).astype(int))

        conn.close()

    except Exception as e:
        print(f"❌ Eroare la analiza DB: {e}")


if __name__ == "__main__":
    analyze_db()
