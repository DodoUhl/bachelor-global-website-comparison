import os
import pandas as pd
import matplotlib.pyplot as plt

# Dateien
INPUT_FILE = "../../csv/html_metrics.csv"
OUTPUT_DIR = "../../charts/html"

os.makedirs(OUTPUT_DIR, exist_ok=True)

# CSV laden
df = pd.read_csv(INPUT_FILE)

# Nur erfolgreich gefundene Webseiten verwenden
df = df[df["found"] == True]

# Numerische Spalten bestimmen
numeric_columns = df.select_dtypes(include="number").columns

for metric in numeric_columns:

    # Länder
    # Nach Länder sortieren -> Mittelwert, Median und Standardabweichung berechenen -> Nach Mittelwert sortieren
    country_stats = (
        df.groupby("country")[metric]
        .agg(["mean", "median", "std"])
        .sort_values("mean", ascending=False)
    )

    plt.figure(figsize=(10, 10))

    # Balken für Mittelwert und Standardabweichung einzeichnen
    plt.bar(
        country_stats.index,
        country_stats["mean"],
        yerr=country_stats["std"],
        capsize=5
    )

    # Median als roten Punkt einzeichnen
    plt.scatter(
        range(len(country_stats)),
        country_stats["median"],
        color="red",
        zorder=5,
        label="Median"
    )

    plt.xticks(rotation=90)

    plt.title(f"{metric} nach Land")
    plt.xlabel("Land")
    plt.ylabel(metric)

    plt.legend()

    plt.tight_layout()

    plt.savefig(
        os.path.join(
            OUTPUT_DIR,
            f"html_{metric}_countries.png"
        )
    )

    plt.close()

    # Kontinente
    # Nach Länder sortieren -> Mittelwert und Median berechenen -> Nach Mittelwert sortieren
    continent_stats = (
        df.groupby("continent")[metric]
        .agg(["mean", "median"])
        .sort_values("mean", ascending=False)
    )

    plt.figure(figsize=(10, 10))

    # Balken für Mittelwert einzeichnen
    plt.bar(
        continent_stats.index,
        continent_stats["mean"]
    )

    # Median als roten Punkt einzeichnen
    plt.scatter(
        range(len(continent_stats)),
        continent_stats["median"],
        color="red",
        zorder=5,
        label="Median"
    )

    plt.title(f"{metric} nach Kontinent")
    plt.xlabel("Kontinent")
    plt.ylabel(metric)

    plt.legend()

    plt.tight_layout()

    plt.savefig(
        os.path.join(
            OUTPUT_DIR,
            f"html_{metric}_continents.png"
        )
    )

    plt.close()

print("Alle HTML-Metrik-Diagramme wurden erstellt.")