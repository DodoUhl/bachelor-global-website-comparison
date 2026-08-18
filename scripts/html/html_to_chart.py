import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

# Dateien
INPUT_FILE = "../../csv/html_metrics.csv"
OUTPUT_DIR = "../../charts/html"

CONTINENT_COLORS = {
    "Europe": "#4DB6E8",
    "Asia": "#FF9F43",
    "Africa": "#66C56C",
    "North America": "#FF6B6B",
    "South America": "#B388EB",
    "Oceania": "#F4D35E"
}

os.makedirs(OUTPUT_DIR, exist_ok=True)

# CSV laden
df = pd.read_csv(INPUT_FILE)

# Nur erfolgreich gefundene Webseiten verwenden
df = df[df["found"] == True]

# Numerische Spalten bestimmen
numeric_columns = df.select_dtypes(include="number").columns

for metric in numeric_columns:

    # Länder
    # Nach Länder sortieren
    country_order = (
        df.groupby("country")[metric]
        .mean()
        .sort_values(ascending=False)
        .index
    )

    # Anzahl Webseiten pro Land
    country_counts = df.groupby("country")[metric].count()

    # Label für Boxplot
    country_labels = [
        f"{country} (n={country_counts[country]})"
        for country in country_order
    ]

    # Größe des Diagramms
    fig, ax = plt.subplots(figsize=(10, 8))

    # Boxplot Diagramm erstellen
    sns.boxplot(
        data=df,
        x=metric,
        y="country",
        hue="continent",
        order=country_order,
        palette=CONTINENT_COLORS,
        dodge=False,
        orient="h",
        width=0.8,
        showmeans=True,
        showfliers=False,
        meanprops={
            "marker": "o",
            "markerfacecolor": "#E5252A",
            "markeredgecolor": "#E5252A",
            "markersize": 8
        },
        medianprops={
            "color": "#333333",
            "linewidth": 2
        },
        boxprops={
            "edgecolor": "#333333",
            "linewidth": 1.5
        },
        whiskerprops={
            "color": "#333333",
            "linewidth": 1.5
        },
        capprops={
            "color": "#333333",
            "linewidth": 1.5
        },
        flierprops={
            "marker": "o",
            "markerfacecolor": "#777777",
            "markeredgecolor": "#777777",
            "markersize": 3,
            "alpha": 0.5
        },
        ax=ax
    )

    # Legende des Diagramms
    legend_elements = [
        Line2D(
            [0],
            [0],
            marker="o",
            color="none",
            markerfacecolor="#E5252A",
            markeredgecolor="#E5252A",
            markersize=8,
            label="Mittelwert"
        ),
        Line2D(
            [0],
            [0],
            color="#333333",
            linewidth=2,
            label="Median"
        ),
        Patch(
            facecolor="white",
            edgecolor="#333333",
            label="Interquartilsabstand (25.–75. Perzentil)"
        ),
        Line2D(
            [0, 1],
            [0, 0],
            color="#333333",
            linewidth=1.5,
            marker="|",
            markevery=[1],
            markersize=10,
            markeredgewidth=1.5,
            label="Whisker (bis 1,5 × IQR)"
        )
    ]

    # Kontinent Legende
    continent_handles = [
        Patch(
            facecolor=color,
            edgecolor="#333333",
            label=continent
        )
        for continent, color in CONTINENT_COLORS.items()
        if continent in df["continent"].unique()
    ]

    # Legende erstellen
    ax.legend(
        handles=legend_elements + continent_handles,
        loc="lower right",
        frameon=True,
        fontsize=10
    )

    # Länderbezeichnungen inklusive Anzahl
    ax.set_yticks(range(len(country_labels)))
    ax.set_yticklabels(country_labels)

    # Titel setzen
    ax.set_title(
        f"{metric} nach Land",
        fontsize=16
    )

    # X- und Y-Achsen Beschriftung
    ax.set_xlabel(metric, fontsize=13)
    ax.set_ylabel("Land", fontsize=13)

    # Nur vertikale Hilfslinien
    ax.grid(axis="x", color="#CCCCCC", linewidth=1)
    ax.grid(axis="y", visible=False)

    sns.despine(ax=ax)

    plt.tight_layout()
    plt.savefig(
        os.path.join(
            OUTPUT_DIR,
            f"html_{metric}_countries.png"
        )
    )

    plt.close()

    # Kontinente
    # Nach Kontinent sortieren
    continent_order = (
        df.groupby("continent")[metric]
        .mean()
        .sort_values(ascending=False)
        .index
    )

    # Anzahl der Webseiten pro Kontinent
    continent_counts = df.groupby("continent")[metric].count()

    # Label für Boxplot
    continent_labels = [
        f"{continent} (n={continent_counts[continent]})"
        for continent in continent_order
    ]

    # Größe des Diagramms
    fig, ax = plt.subplots(figsize=(10, 4))

    #Boxplot Diagramm erstellen
    sns.boxplot(
        data=df,
        x=metric,
        y="continent",
        hue="continent",
        order=continent_order,
        palette=CONTINENT_COLORS,
        dodge=False,
        orient="h",
        width=0.8,
        showmeans=True,
        showfliers=False,
        meanprops={
            "marker": "o",
            "markerfacecolor": "#E5252A",
            "markeredgecolor": "#E5252A",
            "markersize": 8
        },
        medianprops={
            "color": "#333333",
            "linewidth": 2
        },
        boxprops={
            "edgecolor": "#333333",
            "linewidth": 1.5
        },
        whiskerprops={
            "color": "#333333",
            "linewidth": 1.5
        },
        capprops={
            "color": "#333333",
            "linewidth": 1.5
        },
        flierprops={
            "marker": "o",
            "markerfacecolor": "#777777",
            "markeredgecolor": "#777777",
            "markersize": 3,
            "alpha": 0.5
        },
        ax=ax
    )

    # Legende des Diagramms
    legend_elements = [
        Line2D(
            [0],
            [0],
            marker="o",
            color="none",
            markerfacecolor="#E5252A",
            markeredgecolor="#E5252A",
            markersize=8,
            label="Mittelwert"
        ),
        Line2D(
            [0],
            [0],
            color="#333333",
            linewidth=2,
            label="Median"
        ),
        Patch(
            facecolor="#24749D",
            edgecolor="#333333",
            label="Interquartilsabstand (25.–75. Perzentil)"
        ),
        Line2D(
            [0, 1],
            [0, 0],
            color="#333333",
            linewidth=1.5,
            marker="|",
            markevery=[1],
            markersize=10,
            markeredgewidth=1.5,
            label="Whisker (bis 1,5 × IQR)"
        )
    ]

    # Legende erstellen
    ax.legend(
        handles=legend_elements,
        loc="lower right",
        frameon=True,
        fontsize=10
    )

    # Länderbezeichnungen inklusive Anzahl
    ax.set_yticks(range(len(continent_labels)))
    ax.set_yticklabels(continent_labels)

    # Titel setzen
    ax.set_title(
        f"{metric} nach Kontinent",
        fontsize=16
    )

    # X- und Y-Achsen Beschriftung
    ax.set_xlabel(metric, fontsize=13)
    ax.set_ylabel("Kontinent", fontsize=13)

    # Nur vertikale Hilfslinien
    ax.grid(axis="x", color="#CCCCCC", linewidth=1)
    ax.grid(axis="y", visible=False)

    sns.despine(ax=ax)

    plt.tight_layout()
    plt.savefig(
        os.path.join(
            OUTPUT_DIR,
            f"html_{metric}_continents.png"
        )
    )

    plt.close()

print("Alle HTML-Metrik-Diagramme wurden erstellt.")