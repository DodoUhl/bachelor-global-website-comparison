import os
import re
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from sklearn.cluster import KMeans  

# Dateien
INPUT_FILE = "../../csv/visually_metrics.csv"
OUTPUT_DIR = "../../charts/visually"

os.makedirs(OUTPUT_DIR, exist_ok=True)

COLOR_COLUMNS = [
    "dominant_color_1",
    "dominant_color_2",
    "dominant_color_3",
    "dominant_color_4",
    "dominant_color_5"
]

RATIO_COLUMNS = [
    "dominant_color_1_ratio",
    "dominant_color_2_ratio",
    "dominant_color_3_ratio",
    "dominant_color_4_ratio",
    "dominant_color_5_ratio"
]

# RGB in Python-int-Tuple
def parse_rgb(value):
    # Falls Zelle leer
    if pd.isna(value):
        return None

    # NumPy-Bezeichnung entfernen
    cleaned_value = re.sub(r"np\.\w+", "", str(value))

    # Ganzen Zahlen suchen
    numbers = re.findall(r"-?\d+", cleaned_value)

    if len(numbers) < 3:
        return None

    # Tupel als Ganzzahl zurückgeben
    return tuple(max(0, min(255, int(number))) for number in numbers[:3])

# Farbe für 5 Gruppen erstellen
def calculate_representative_palette(group, color_columns, ratio_columns, number_of_colors=5):
    colors = []
    color_weights = []

    # Nur gültige Farben in colors und color_weights speichern
    for color_column, ratio_column in zip(color_columns,ratio_columns):
        parsed_colors = group[color_column].apply(parse_rgb)
        ratios = pd.to_numeric(group[ratio_column])

        for color, weight in zip(parsed_colors,ratios):
            if (color is not None and pd.notna(weight) and weight > 0 ):
                colors.append(color)
                color_weights.append(float(weight))

    if not colors:
        return [], []

    # Listen in NumPy-Arrays umwandeln für K-Means
    colors = np.asarray(colors, dtype=float)
    color_weights = np.asarray(color_weights, dtype=float)
    
    # Doppelte Farben entfernen, um K-Means-Warnungen zu vermeiden
    unique_colors = np.unique(colors, axis=0)

    # Clusteranzahl bestimmen
    number_of_clusters = min(number_of_colors, len(unique_colors))

    if number_of_clusters == 0:
        return [], []

    # K-Means vorbereiten mit 5 Cluster und 10 Startpunkten
    kmeans = KMeans(n_clusters=number_of_clusters, random_state=42, n_init=10)

    # K-Means ausführen
    kmeans.fit(colors, sample_weight=color_weights)

    # Zuordnung von Farbe zu Cluster
    cluster_labels = kmeans.labels_

    # Summe der Pixelanteile aller Farben eines Clusters
    cluster_weights = np.bincount(cluster_labels, weights=color_weights, minlength=number_of_clusters)

    # Gewichtete Anteile auf eine Summe von 1 normieren
    cluster_ratios = (cluster_weights / cluster_weights.sum())

    # Häufigstes Farbcluster zuerst
    cluster_order = np.argsort(cluster_ratios)[::-1]

    # RGB-Farbe aus Cluster Zentrum erzeugen
    palette = (kmeans.cluster_centers_[cluster_order].round().clip(0, 255).astype(int))

    # Farbanteil in selber Reihenfolge wie Farben sortieren
    sorted_ratios = cluster_ratios[cluster_order]

    # NumPy-Werte in int Werte umwandeln
    palette = [tuple(int(value) for value in color) for color in palette]
    sorted_ratios = [float(ratio) for ratio in sorted_ratios]

    return palette, sorted_ratios

# Farb-Diagramm erzeugen
def create_palette_chart(dataframe, group_column, color_columns, ratio_columns, title, output_file):
    # Gruppe bestimmen (Entweder country oder continent)
    groups = sorted(dataframe[group_column].dropna().unique())

    figure_height = max(6, len(groups) * 0.35)

    # Abbildung und Achse erstellen
    fig, ax = plt.subplots(figsize=(10, figure_height))

    for row, group_name in enumerate(groups):
        group_data = dataframe[dataframe[group_column] == group_name]

        # Farbpalette berechnen
        palette, palette_ratios = calculate_representative_palette(
            group=group_data,
            color_columns=color_columns,
            ratio_columns=ratio_columns,
            number_of_colors=5
        )

        # Rundungsdifferenz beim größten Anteil ausgleichen
        display_percentages = np.round(np.asarray(palette_ratios) * 100, 2)
        difference = round(100.0 - display_percentages.sum(), 2)
        display_percentages[np.argmax(display_percentages)] += difference

        for column, (color, ratio) in enumerate(zip(palette, display_percentages)):
            # RGB-Werte normalisieren für Matplot (0-1)
            normalized_color = (np.asarray(color) / 255)

            # Rechteck mit richtiger Farbe erstellen und positionieren
            rectangle = Rectangle((column, row - 0.4), width=1, height=0.8, facecolor=normalized_color, edgecolor="white", linewidth=1)
            ax.add_patch(rectangle)

            # Wahrgenommene Helligkeit der Farbe bestimmen
            luminance = (0.299 * color[0] + 0.587 * color[1] + 0.114 * color[2])

            # Auf dunklen Farben weiße Schrift verwenden und umgekehrt
            text_color = ("black" if luminance > 150 else "white")

            # Prozentwert als Text auf Rechteck hinzufügen
            ax.text(column + 0.5, row, f"{ratio:.2f} %", ha="center", va="center", color=text_color, fontsize=8, fontweight="bold")

    # Achsenbereich einstellen
    ax.set_xlim(0, 5)
    ax.set_ylim(-0.5, len(groups) - 0.5)

    # Beschriftung der x-Achse
    ax.set_xticks(np.arange(5) + 0.5)
    ax.set_xticklabels(["Farbe 1", "Farbe 2", "Farbe 3", "Farbe 4", "Farbe 5"])

    # Beschriftung der y-Achse
    ax.set_yticks(range(len(groups)))
    ax.set_yticklabels(groups)

    # Alphabetisch erster Eintrag oben
    ax.invert_yaxis()

    ax.set_title(title)

    ax.set_xlabel(
        "Repräsentative Farben, "
        "nach gewichtetem Anteil sortiert"
    )

    ax.set_ylabel(
        "Land"
        if group_column == "country"
        else "Kontinent"
    )

    ax.tick_params(
        axis="both",
        length=0
    )

    for spine in ax.spines.values():
        spine.set_visible(False)

    plt.tight_layout()

    plt.savefig(
        output_file,
        bbox_inches="tight"
    )

    plt.close()

# CSV laden
df = pd.read_csv(INPUT_FILE)

# Nur erfolgreich gefundene Webseiten verwenden
df = df[df["found"] == True]

# Alle numerischen Spalten bestimmen
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
            f"visually_{metric}_countries.png"
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
            f"visually_{metric}_continents.png"
        )
    )

    plt.close()

create_palette_chart(
    dataframe=df,
    group_column="country",
    color_columns=COLOR_COLUMNS,
    ratio_columns=RATIO_COLUMNS,
    title="Dominante Farben nach Land",
    output_file=os.path.join(
        OUTPUT_DIR,
        "visually_dominant_colors_countries.png"
    )
)

create_palette_chart(
    dataframe=df,
    group_column="continent",
    color_columns=COLOR_COLUMNS,
    ratio_columns=RATIO_COLUMNS,
    title="Dominante Farben nach Kontinent",
    output_file=os.path.join(
        OUTPUT_DIR,
        "visually_dominant_colors_continents.png"
    )
)

print("Alle Visuell-Metrik-Diagramme wurden erstellt.")