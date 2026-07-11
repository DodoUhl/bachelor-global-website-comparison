import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

# Dateien
INPUT_FILE = "../../websites/language_percentage_by_country.csv"
OUTPUT_FILE = "../../charts/language_percentage_chart.png"
PERCENT_COLUMN = "percent_of_detected"

# Daten einlesen und vorbereiten
df = pd.read_csv(INPUT_FILE)
df = df.dropna(subset=[PERCENT_COLUMN])
df = df[df["detected_websites"] > 30]
df = df[df[PERCENT_COLUMN] > 0] 
df = df.sort_values(PERCENT_COLUMN, ascending=True)
df["label"] = (df["country"] + " (" + df["detected_websites"].astype(int).astype(str) + ")")

# Chart erstellen
plt.figure(figsize=(10, 10))
plt.barh(df["label"], df[PERCENT_COLUMN])
plt.xlabel("Webseiten mit passender Sprache (%)")
plt.ylabel("Land")
plt.title("Anteil der Webseiten mit passender Landessprache nach ccTLD")
plt.xlim(0, 100)

# Prozentwerte neben den Balken anzeigen
for index, value in enumerate(df[PERCENT_COLUMN]):
    plt.text(
        value + 1,
        index,
        f"{value:.1f}%",
        va="center"
    )
plt.tight_layout()

# Ergebnisse speichern und anzeigen
Path(OUTPUT_FILE).parent.mkdir(parents=True, exist_ok=True)
plt.savefig(OUTPUT_FILE, dpi=300)
print(f"Chart gespeichert unter: {OUTPUT_FILE}")