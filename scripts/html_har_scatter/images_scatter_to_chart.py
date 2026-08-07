import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

HTML_FILE = "../../csv/html_metrics.csv"
HAR_FILE = "../../csv/har_metrics.csv"
OUTPUT_DIR = "../../charts/har"

CONTINENT_COLORS = {
    "Europe": "#4DB6E8",
    "Asia": "#FF9F43",
    "Africa": "#66C56C",
    "North America": "#FF6B6B",
    "South America": "#B388EB",
    "Oceania": "#F4D35E"
}

os.makedirs(OUTPUT_DIR, exist_ok=True)

html_df = pd.read_csv(HTML_FILE)
har_df = pd.read_csv(HAR_FILE)

# Bildmetriken eindeutig benennen
html_images_df = html_df[
    ["continent", "country", "website", "images"]
].rename(
    columns={"images": "html_images"}
)

har_images_df = har_df[
    ["country", "website", "images"]
].rename(
    columns={"images": "har_images"}
)

# Nur Webseiten verwenden, die in beiden Dateien vorkommen
df = html_images_df.merge(
    har_images_df,
    on=["country", "website"],
    how="inner",
    validate="one_to_one"
)
SCATTER_PLOTS = [
    {
        "x_metric": "html_images",
        "y_metric": "har_images",
        "x_label": "Anzahl der img-Elemente",
        "y_label": "Anzahl geladener Bildressourcen",
        "title": (
            "Zusammenhang zwischen img-Elementen "
            "und geladenen Bildressourcen"
        ),
        "output_filename": (
            "har_html_images.png"
        )
    }
]
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