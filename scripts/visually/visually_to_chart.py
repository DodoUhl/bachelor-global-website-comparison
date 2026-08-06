import os
import re
import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Patch
from sklearn.cluster import KMeans 
from matplotlib.lines import Line2D

# Dateien
INPUT_FILE = "../../csv/visually_metrics.csv"
OUTPUT_DIR = "../../charts/visually"

os.makedirs(OUTPUT_DIR, exist_ok=True)

# Einheitliches aussehen der Diagramme
sns.set_theme(style="whitegrid", context="notebook")

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

CONTINENT_COLORS = {
    "Europe": "#4DB6E8",
    "Asia": "#FF9F43",
    "Africa": "#66C56C",
    "North America": "#FF6B6B",
    "South America": "#B388EB",
    "Oceania": "#F4D35E"
}

PLOT_METRICS = [
    "unique_colors",
    "color_entropy",
    "average_saturation",
    "average_brightness",
    "whitespace_ratio",
    "screenshot_height",
    "screenshot_file_size"
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
    ax.grid(False)

    sns.despine(
        ax=ax,
        left=True,
        bottom=True
    )

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

for metric in PLOT_METRICS:

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
    fig, ax = plt.subplots(figsize=(10, 10))

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
            f"visually_{metric}_countries.png"
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
    fig, ax = plt.subplots(figsize=(10, 10))

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
# 2 Metriken zusammen plotten
SCATTER_PLOTS = [
    {
        "x_metric": "screenshot_height",
        "y_metric": "screenshot_file_size_mib",
        "x_label": "Screenshot-Höhe in Pixeln",
        "y_label": "Screenshot-Dateigröße in MiB",
        "title": (
            "Zusammenhang zwischen Screenshot-Höhe "
            "und Dateigröße"
        ),
        "output_filename": (
            "visually_screenshot_height_file_size.png"
        )
    },
    {
        "x_metric": "unique_colors",
        "y_metric": "color_entropy",
        "x_label": "Anzahl einzigartiger Farben",
        "y_label": "Farbenentropie",
        "title": (
            "Zusammenhang zwischen Farbanzahl "
            "und Farbenentropie"
        ),
        "output_filename": (
            "visually_unique_colors_color_entropy.png"
        )
    },
    {
        "x_metric": "average_brightness",
        "y_metric": "whitespace_ratio",
        "x_label": "Durchschnittliche Helligkeit",
        "y_label": "Weißraumanteil",
        "title": (
            "Zusammenhang zwischen Helligkeit "
            "und Weißraumanteil"
        ),
        "output_filename": (
            "visually_brightness_whitespace.png"
        )
    },
    {
        "x_metric": "unique_colors",
        "y_metric": "screenshot_file_size_mib",
        "x_label": "Anzahl einzigartiger Farben",
        "y_label": "Screenshot-Dateigröße in MiB",
        "title": (
            "Zusammenhang zwischen Farbanzahl "
            "und Screenshot-Dateigröße"
        ),
        "output_filename": (
            "visually_unique_colors_file_size.png"
        )
    },
    {
        "x_metric": "screenshot_height",
        "y_metric": "whitespace_ratio",
        "x_label": "Screenshot-Höhe in Pixeln",
        "y_label": "Weißraumanteil",
        "title": (
            "Zusammenhang zwischen Screenshot-Höhe "
            "und Weißraumanteil"
        ),
        "output_filename": (
            "visually_screenshot_height_whitespace.png"
        )
    }
]

# Größe in MiB umrechnen
df["screenshot_file_size_mib"] = (df["screenshot_file_size"] / (1024 ** 2))

for plot in SCATTER_PLOTS:
    x_metric = plot["x_metric"]
    y_metric = plot["y_metric"]

    # Daten für das Diagramm aus 2 Metriken
    scatter_data = df.dropna(
        subset=[
            x_metric,
            y_metric,
            "continent"
        ]
    )

    # Korrelation aus beiden Metriken berechnen
    correlation = scatter_data[
        [x_metric, y_metric]
    ].corr(method="spearman").iloc[0, 1]

    # Größe des Diagramms
    fig, ax = plt.subplots(figsize=(10, 10))

    # Streu-Diagramm erstellen
    sns.scatterplot(
        data=scatter_data,
        x=x_metric,
        y=y_metric,
        hue="continent",
        palette=CONTINENT_COLORS,
        alpha=0.7,
        s=55,
        edgecolor="white",
        linewidth=0.5,
        ax=ax
    )

    # Korrelation Text hinzufügen
    ax.text(
        0.02,
        0.98,
        f"Spearman-Korrelation: r = {correlation:.2f}",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=11,
        bbox={
            "facecolor": "white",
            "edgecolor": "#999999",
            "alpha": 0.9
        }
    )

    # Titel setzen
    ax.set_title(plot["title"], fontsize=16)

    # X- und Y-Achsen Beschriftung
    ax.set_xlabel(plot["x_label"], fontsize=13)
    ax.set_ylabel(plot["y_label"], fontsize=13)

    # Nur vertikale Hilfslinien
    ax.grid(
        color="#CCCCCC",
        linewidth=1
    )

    # Legende erstellen
    ax.legend(
        title="Kontinent",
        frameon=True
    )

    sns.despine(ax=ax)

    plt.tight_layout()
    plt.savefig(
        os.path.join(
            OUTPUT_DIR,
            plot["output_filename"]
        ),
        bbox_inches="tight"
    )

    plt.close()

print("Alle Visuell-Metrik-Diagramme wurden erstellt.")