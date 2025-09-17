import pandas as pd

def analyze_trades(file="trades_log.csv"):
    try:
        df = pd.read_csv(file)

        # verificăm că există coloanele necesare
        if not {"Tip", "Profit %"}.issubset(df.columns):
            print("⚠️ Fișierul nu conține coloanele necesare (Tip, Profit %).")
            return

        # conversie Profit % la numeric
        df["Profit %"] = pd.to_numeric(df["Profit %"], errors="coerce").fillna(0)

        # filtrăm doar tranzacțiile reale de SELL
        sells = df[df["Tip"].isin(["SELL_TP", "SELL_SL", "SELL"])].copy()

        total_trades = len(sells)
        wins = len(sells[sells["Profit %"] > 0])
        losses = len(sells[sells["Profit %"] <= 0])
        cum_profit = sells["Profit %"].sum()

        print("📊 Rezumat tranzacții executate:")
        print(f"   Total vânzări: {total_trades}")
        print(f"   Profitabile: {wins}")
        print(f"   Pierdere: {losses}")
        print(f"   Profit cumulat: {cum_profit:.2f}%")

        print("\n🔍 Ultimele tranzacții:")
        print(sells.tail(10))

    except FileNotFoundError:
        print(f"⚠️ Fișierul {file} nu a fost găsit.")
    except Exception as e:
        print(f"❌ Eroare la analiză: {e}")


if __name__ == "__main__":
    analyze_trades()
