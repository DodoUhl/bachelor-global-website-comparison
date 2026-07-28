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

def parse_rgb(value):
    if pd.isna(value):
        return None

    cleaned_value = re.sub(
        r"np\.\w+",
        "",
        str(value)
    )

    numbers = re.findall(
        r"-?\d+",
        cleaned_value
    )

    if len(numbers) < 3:
        return None

    return tuple(
        max(0, min(255, int(number)))
        for number in numbers[:3]
    )

# Gemeinsame Farbe für 5 Gruppen erstellen
def calculate_representative_palette(group, color_columns, ratio_columns, number_of_colors=5):
    colors = []
    color_weights = []

    # Nur gültige Farben in colors speichern
    for color_column, ratio_column in zip(color_columns,ratio_columns):
        parsed_colors = group[color_column].apply(parse_rgb)
        ratios = pd.to_numeric(group[ratio_column])

        for color, weight in zip(parsed_colors,ratios):
            if (color is not None and pd.notna(weight) and weight > 0 ):
                colors.append(color)
                color_weights.append(float(weight))

    if not colors:
        return []

    colors = np.asarray(colors, dtype=float)
    color_weights = np.asarray(color_weights, dtype=float)
    
    # Doppelte Farben entfernen, um K-Means-Warnungen zu vermeiden
    unique_colors = np.unique(colors, axis=0)

    number_of_clusters = min(
        number_of_colors,
        len(unique_colors)
    )

    if number_of_clusters == 0:
        return []

    kmeans = KMeans(
        n_clusters=number_of_clusters,
        random_state=42,
        n_init=10
    )

    kmeans.fit(colors, sample_weight=color_weights)

    cluster_labels = kmeans.labels_


    cluster_weights = np.bincount(
        cluster_labels,
        weights=color_weights,
        minlength=number_of_clusters
    )

    # Häufigstes Farbcluster zuerst
    cluster_order = np.argsort(cluster_weights)[::-1]

    palette = (
        kmeans.cluster_centers_[cluster_order]
        .round()
        .clip(0, 255)
        .astype(int)
    )
    print([tuple(int(value) for value in color) for color in palette])
    return [tuple(int(value) for value in color) for color in palette]

def create_palette_chart(
    dataframe,
    group_column,
    color_columns,
    ratio_columns,
    title,
    output_file
):
    """
    Erstellt für jedes Land beziehungsweise jeden Kontinent
    eine Zeile mit fünf repräsentativen Farbfeldern.
    """
    groups = sorted(
        dataframe[group_column]
        .dropna()
        .unique()
    )

    figure_height = max(
        6,
        len(groups) * 0.35
    )

    fig, ax = plt.subplots(
        figsize=(10, figure_height)
    )

    for row, group_name in enumerate(groups):
        group_data = dataframe[
            dataframe[group_column] == group_name
        ]

        palette = calculate_representative_palette(
            group=group_data,
            color_columns=color_columns,
            ratio_columns=ratio_columns,
            number_of_colors=5
        )

        for column, color in enumerate(palette):
            normalized_color = (
                np.asarray(color) / 255
            )

            rectangle = Rectangle(
                (column, row - 0.4),
                width=1,
                height=0.8,
                facecolor=normalized_color,
                edgecolor="white",
                linewidth=1
            )

            ax.add_patch(rectangle)

    ax.set_xlim(0, 5)
    ax.set_ylim(
        -0.5,
        len(groups) - 0.5
    )

    ax.set_xticks(
        np.arange(5) + 0.5
    )

    ax.set_xticklabels([
        "Farbe 1",
        "Farbe 2",
        "Farbe 3",
        "Farbe 4",
        "Farbe 5"
    ])

    ax.set_yticks(
        range(len(groups))
    )

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
        dpi=300,
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

if COLOR_COLUMNS:

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