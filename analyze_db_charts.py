import psycopg2
import os
import pandas as pd
import matplotlib.pyplot as plt

def analyze_db_charts():
    try:
        conn = psycopg2.connect(os.getenv("DATABASE_URL"))
        print("✅ Conectat la baza de date\n")

        # === Profit în timp ===
        trades_query = """
            SELECT timestamp, symbol, action, profit_pct
            FROM trades
            WHERE action LIKE 'SELL%'
              AND status = 'EXECUTED'
            ORDER BY timestamp
        """
        trades_df = pd.read_sql(trades_query, conn)

        if not trades_df.empty:
            trades_df['cumulative_profit'] = trades_df['profit_pct'].cumsum()

            plt.figure(figsize=(10,5))
            plt.plot(trades_df['timestamp'], trades_df['cumulative_profit'], marker='o')
            plt.title("📈 Profit cumulativ în timp")
            plt.xlabel("Timp")
            plt.ylabel("Profit %")
            plt.xticks(rotation=45)
            plt.grid(True)
            plt.tight_layout()
            plt.show()
        else:
            print("⚠️ Nu există tranzacții executate pentru a calcula profitul.\n")

        # === Distribuția semnalelor ===
        signals_query = """
            SELECT symbol, signal, COUNT(*) as cnt
            FROM signals
            GROUP BY symbol, signal
            ORDER BY symbol, signal
        """
        signals_df = pd.read_sql(signals_query, conn)

        if not signals_df.empty:
            pivot_df = signals_df.pivot(index="symbol", columns="signal", values="cnt").fillna(0).astype(int)

            pivot_df.plot(kind="bar", figsize=(10,5))
            plt.title("📊 Distribuția semnalelor pe monede")
            plt.xlabel("Monedă")
            plt.ylabel("Număr semnale")
            plt.xticks(rotation=0)
            plt.legend(title="Semnal")
            plt.tight_layout()
            plt.show()
        else:
            print("⚠️ Nu există semnale înregistrate în DB.\n")

        conn.close()

    except Exception as e:
        print(f"❌ Eroare la analiza DB cu grafice: {e}")


if __name__ == "__main__":
    analyze_db_charts()
