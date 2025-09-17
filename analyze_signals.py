import pandas as pd
from datetime import datetime, timedelta

def analyze_signals(file="signals_log.csv"):
    try:
        df = pd.read_csv(file)

        # conversie coloană Timp la datetime
        df["Timp"] = pd.to_datetime(df["Timp"], errors="coerce")

        # filtrăm ultimele 24h
        cutoff = datetime.now() - timedelta(hours=24)
        df_24h = df[df["Timp"] >= cutoff]

        if df_24h.empty:
            print("⚠️ Nu există semnale în ultimele 24h.")
            return

        # numărăm câte semnale de fiecare tip
        counts = df_24h["Semnal"].value_counts()

        print("📊 Semnale generate în ultimele 24h:")
        for semnal, nr in counts.items():
            print(f"   {semnal}: {nr}")

        # distribuția pe simboluri
        counts_symbol = df_24h.groupby(["Simbol", "Semnal"]).size().unstack(fill_value=0)

        print("\n🔍 Detalii pe simboluri (ultimele 24h):")
        print(counts_symbol)

    except FileNotFoundError:
        print(f"⚠️ Fișierul {file} nu a fost găsit.")
    except Exception as e:
        print(f"❌ Eroare la analiză: {e}")


if __name__ == "__main__":
    analyze_signals()
