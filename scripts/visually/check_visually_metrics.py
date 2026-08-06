import ast
import pandas as pd

REFERENCE_FILE = "../../websites/top100_websites.csv"
METRICS_FILE = "../../csv/visually_metrics.csv"

KEY_COLUMNS = ["country", "website"]

COLOR_COLUMNS = [
    "dominant_color_1",
    "dominant_color_2",
    "dominant_color_3",
    "dominant_color_4",
    "dominant_color_5"
]

NUMERIC_COLUMNS = [
    "unique_colors",
    "color_entropy",
    "average_saturation",
    "average_brightness",
    "whitespace_ratio",
    "screenshot_height",
    "screenshot_file_size"
]

METRIC_COLUMNS = COLOR_COLUMNS + NUMERIC_COLUMNS


def is_missing(series):
    return (
        series.isna()
        | series.astype(str).str.strip().str.lower().isin(
            ["", "none", "nan", "null"]
        )
    )


def convert_found(series):
    return series.astype(str).str.strip().str.lower().map({
        "true": True,
        "1": True,
        "yes": True,
        "false": False,
        "0": False,
        "no": False
    })


def valid_rgb(value):
    if pd.isna(value):
        return False

    try:
        rgb = ast.literal_eval(str(value))

        return (
            isinstance(rgb, (tuple, list))
            and len(rgb) == 3
            and all(
                isinstance(number, (int, float))
                and 0 <= number <= 255
                for number in rgb
            )
        )

    except (ValueError, SyntaxError):
        return False


reference_df = pd.read_csv(
    REFERENCE_FILE,
    sep=None,
    engine="python",
    encoding="utf-8-sig"
)

metrics_df = pd.read_csv(
    METRICS_FILE,
    sep=None,
    engine="python",
    encoding="utf-8-sig"
)

reference_df.columns = (
    reference_df.columns
    .str.replace("\ufeff", "", regex=False)
    .str.strip()
)

metrics_df.columns = (
    metrics_df.columns
    .str.replace("\ufeff", "", regex=False)
    .str.strip()
)

print("=== VOLLSTÄNDIGKEITSPRÜFUNG: VISUELLE METRIKEN ===")
print(f"Erwartete Webseiten: {len(reference_df)}")
print(f"Vorhandene Einträge: {len(metrics_df)}")

missing_reference_columns = [
    column for column in KEY_COLUMNS
    if column not in reference_df.columns
]

required_columns = KEY_COLUMNS + ["found", "crawl_id"] + METRIC_COLUMNS

missing_metric_columns = [
    column for column in required_columns
    if column not in metrics_df.columns
]

if missing_reference_columns:
    print(
        "\nFehlende Schlüsselspalten in der Ausgangsliste: "
        f"{missing_reference_columns}"
    )
    raise SystemExit

if missing_metric_columns:
    print(
        "\nFehlende Spalten in der visuellen Metrikdatei: "
        f"{missing_metric_columns}"
    )
    print("Vorhandene Spalten:")
    print(metrics_df.columns.tolist())
    raise SystemExit

reference_duplicates = reference_df.duplicated(
    subset=KEY_COLUMNS,
    keep=False
)

metric_duplicates = metrics_df.duplicated(
    subset=KEY_COLUMNS,
    keep=False
)

print(
    f"Doppelte Einträge in der Ausgangsliste: "
    f"{reference_duplicates.sum()}"
)

print(
    f"Doppelte Einträge in der Ergebnisdatei: "
    f"{metric_duplicates.sum()}"
)

reference_keys = reference_df[KEY_COLUMNS].drop_duplicates()
metric_keys = metrics_df[KEY_COLUMNS].drop_duplicates()

missing_websites = (
    reference_keys
    .merge(
        metric_keys,
        on=KEY_COLUMNS,
        how="left",
        indicator=True
    )
    .query("_merge == 'left_only'")
    .drop(columns="_merge")
)

unexpected_websites = (
    metric_keys
    .merge(
        reference_keys,
        on=KEY_COLUMNS,
        how="left",
        indicator=True
    )
    .query("_merge == 'left_only'")
    .drop(columns="_merge")
)

print(f"Fehlende Webseiten: {len(missing_websites)}")
print(f"Unerwartete Webseiten: {len(unexpected_websites)}")

found = convert_found(metrics_df["found"])
unknown_found = found.isna()

crawl_id_missing = is_missing(metrics_df["crawl_id"])

metric_values_missing = metrics_df[METRIC_COLUMNS].apply(
    is_missing
)

incomplete_metrics = metric_values_missing.any(axis=1)

found_without_crawl = (
    found.eq(True)
    & crawl_id_missing
)

found_without_metrics = (
    found.eq(True)
    & incomplete_metrics
)

crawl_despite_not_found = (
    found.eq(False)
    & ~crawl_id_missing
)

print("\n=== ABGLEICH VON FOUND, CRAWL-ID UND METRIKEN ===")
print(
    f"Ungültiger oder unbekannter found-Status: "
    f"{unknown_found.sum()}"
)
print(
    f"found=True, aber Crawl-ID fehlt: "
    f"{found_without_crawl.sum()}"
)
print(
    f"found=True, aber Metrikwerte fehlen: "
    f"{found_without_metrics.sum()}"
)
print(
    f"found=False, aber Crawl-ID vorhanden: "
    f"{crawl_despite_not_found.sum()}"
)

numeric_metrics = metrics_df[NUMERIC_COLUMNS].apply(
    pd.to_numeric,
    errors="coerce"
)

invalid_numeric_values = (
    numeric_metrics.isna().any(axis=1)
    & found.eq(True)
)

negative_values = (
    (numeric_metrics < 0).any(axis=1)
    & found.eq(True)
)

invalid_whitespace = (
    ~numeric_metrics["whitespace_ratio"].between(0, 1)
    & found.eq(True)
)

invalid_saturation = (
    ~numeric_metrics["average_saturation"].between(0, 255)
    & found.eq(True)
)

invalid_brightness = (
    ~numeric_metrics["average_brightness"].between(0, 255)
    & found.eq(True)
)

invalid_dimensions = (
    (
        numeric_metrics["screenshot_height"].le(0)
        | numeric_metrics["screenshot_file_size"].le(0)
    )
    & found.eq(True)
)

invalid_unique_colors = (
    numeric_metrics["unique_colors"].lt(1)
    & found.eq(True)
)

invalid_entropy = (
    numeric_metrics["color_entropy"].lt(0)
    & found.eq(True)
)

invalid_colors = pd.Series(
    False,
    index=metrics_df.index
)

for column in COLOR_COLUMNS:
    invalid_colors |= ~metrics_df[column].apply(valid_rgb)

invalid_colors &= found.eq(True)

valid_rows = (
    found.eq(True)
    & ~crawl_id_missing
    & ~incomplete_metrics
    & ~invalid_numeric_values
    & ~negative_values
    & ~invalid_whitespace
    & ~invalid_saturation
    & ~invalid_brightness
    & ~invalid_dimensions
    & ~invalid_unique_colors
    & ~invalid_entropy
    & ~invalid_colors
)

print("\n=== PLAUSIBILITÄTSPRÜFUNG ===")
print(
    f"Zeilen mit nicht numerischen Metrikwerten: "
    f"{invalid_numeric_values.sum()}"
)
print(
    f"Zeilen mit negativen Metrikwerten: "
    f"{negative_values.sum()}"
)
print(
    f"Ungültiger Weißraumanteil: "
    f"{invalid_whitespace.sum()}"
)
print(
    f"Ungültige durchschnittliche Sättigung: "
    f"{invalid_saturation.sum()}"
)
print(
    f"Ungültige durchschnittliche Helligkeit: "
    f"{invalid_brightness.sum()}"
)
print(
    f"Ungültige Screenshot-Dateigröße oder -Höhe: "
    f"{invalid_dimensions.sum()}"
)
print(
    f"Ungültige Anzahl eindeutiger Farben: "
    f"{invalid_unique_colors.sum()}"
)
print(
    f"Ungültige Farbinformation: "
    f"{invalid_entropy.sum()}"
)
print(
    f"Ungültige dominante RGB-Farben: "
    f"{invalid_colors.sum()}"
)
print(
    f"Vollständig auswertbare Messungen: "
    f"{valid_rows.sum()}"
)
print(
    f"Nicht vollständig auswertbare Messungen: "
    f"{(~valid_rows).sum()}"
)

all_correct = (
    len(reference_df) == 6000
    and len(metrics_df) == 6000
    and not reference_duplicates.any()
    and not metric_duplicates.any()
    and missing_websites.empty
    and unexpected_websites.empty
    and not unknown_found.any()
    and not found_without_crawl.any()
    and not found_without_metrics.any()
    and not crawl_despite_not_found.any()
    and not invalid_numeric_values.any()
    and not negative_values.any()
    and not invalid_whitespace.any()
    and not invalid_saturation.any()
    and not invalid_brightness.any()
    and not invalid_dimensions.any()
    and not invalid_unique_colors.any()
    and not invalid_entropy.any()
    and not invalid_colors.any()
    and valid_rows.all()
)

print("\n=== GESAMTERGEBNIS ===")

if all_correct:
    print(
        "Die visuelle Metrikdatei ist vollständig und plausibel."
    )
else:
    print(
        "Die visuelle Metrikdatei enthält Auffälligkeiten."
    )

if not missing_websites.empty:
    print("\nBeispiele fehlender Webseiten:")
    print(
        missing_websites
        .head(20)
        .to_string(index=False)
    )

if not unexpected_websites.empty:
    print("\nBeispiele unerwarteter Webseiten:")
    print(
        unexpected_websites
        .head(20)
        .to_string(index=False)
    )

if metric_duplicates.any():
    print("\nBeispiele mehrfach vorhandener Webseiten:")
    print(
        metrics_df.loc[
            metric_duplicates,
            KEY_COLUMNS
        ]
        .head(20)
        .to_string(index=False)
    )

if found_without_metrics.any():
    print("\nBeispiele mit found=True, aber fehlenden Metriken:")
    print(
        metrics_df.loc[
            found_without_metrics,
            KEY_COLUMNS + ["crawl_id"]
        ]
        .head(20)
        .to_string(index=False)
    )

invalid_rows = ~valid_rows

if invalid_rows.any():
    print("\nBeispiele nicht vollständig auswertbarer Messungen:")
    print(
        metrics_df.loc[
            invalid_rows,
            KEY_COLUMNS + ["found", "crawl_id"] + METRIC_COLUMNS
        ]
        .head(20)
        .to_string(index=False)
    )