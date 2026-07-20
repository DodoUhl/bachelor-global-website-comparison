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

# "found" (0/1 bzw. bool) ausschließen
numeric_columns = [col for col in numeric_columns if col != "found"]

for metric in numeric_columns:

    # Länder
    country_stats = (
        df.groupby("country")[metric]
        .agg(["mean", "median", "std"])
        .sort_values("mean", ascending=False)
    )

    plt.figure(figsize=(10, 10))

    plt.bar(
        country_stats.index,
        country_stats["mean"],
        yerr=country_stats["std"],
        capsize=5
    )

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
            f"{metric}_countries.png"
        ),
        dpi=300
    )

    plt.close()

    # Kontinente
    continent_stats = (
        df.groupby("continent")[metric]
        .agg(["mean", "median"])
        .sort_values("mean", ascending=False)
    )

    plt.figure(figsize=(10, 10))

    plt.bar(
        continent_stats.index,
        continent_stats["mean"]
    )

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
            f"{metric}_continents.png"
        ),
        dpi=300
    )

    plt.close()

print("Alle HTML-Metrik-Diagramme wurden erstellt.")