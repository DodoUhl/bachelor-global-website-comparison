import pandas as pd

REFERENCE_FILE = "../../websites/top100_websites.csv"
METRICS_FILE = "../../csv/html_metrics.csv"

KEY_COLUMNS = ["country", "website"]

METRIC_COLUMNS = [
    "dom_size",
    "links",
    "images",
    "forms",
    "tables",
    "buttons",
    "text_chars",
    "text_words",
    "text_blocks"
]


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

print("=== VOLLSTÄNDIGKEITSPRÜFUNG: HTML-METRIKEN ===")
print(f"Erwartete Webseiten: {len(reference_df)}")
print(f"Vorhandene Einträge: {len(metrics_df)}")

required_columns = KEY_COLUMNS + ["found", "crawl_id"] + METRIC_COLUMNS
missing_columns = [
    column for column in required_columns
    if column not in metrics_df.columns
]

if missing_columns:
    print(f"\nFehlende Spalten: {missing_columns}")
    raise SystemExit

reference_duplicates = reference_df.duplicated(
    subset=KEY_COLUMNS, keep=False
)
metric_duplicates = metrics_df.duplicated(
    subset=KEY_COLUMNS, keep=False
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
    .merge(metric_keys, on=KEY_COLUMNS, how="left", indicator=True)
    .query("_merge == 'left_only'")
    .drop(columns="_merge")
)

unexpected_websites = (
    metric_keys
    .merge(reference_keys, on=KEY_COLUMNS, how="left", indicator=True)
    .query("_merge == 'left_only'")
    .drop(columns="_merge")
)

print(f"Fehlende Webseiten: {len(missing_websites)}")
print(f"Unerwartete Webseiten: {len(unexpected_websites)}")

found = convert_found(metrics_df["found"])
unknown_found = found.isna()

crawl_id_missing = is_missing(metrics_df["crawl_id"])
metric_values_missing = metrics_df[METRIC_COLUMNS].apply(is_missing)
incomplete_metrics = metric_values_missing.any(axis=1)

found_without_crawl = found.eq(True) & crawl_id_missing
found_without_metrics = found.eq(True) & incomplete_metrics
crawl_despite_not_found = found.eq(False) & ~crawl_id_missing

print("\n=== ABGLEICH VON FOUND, CRAWL-ID UND METRIKEN ===")
print(f"Ungültiger oder unbekannter found-Status: {unknown_found.sum()}")
print(f"found=True, aber Crawl-ID fehlt: {found_without_crawl.sum()}")
print(f"found=True, aber Metrikwerte fehlen: {found_without_metrics.sum()}")
print(
    f"found=False, aber Crawl-ID vorhanden: "
    f"{crawl_despite_not_found.sum()}"
)

numeric_metrics = metrics_df[METRIC_COLUMNS].apply(
    pd.to_numeric, errors="coerce"
)

negative_values = (numeric_metrics < 0).any(axis=1)

valid_rows = (
    found.eq(True)
    & ~crawl_id_missing
    & ~incomplete_metrics
    & ~negative_values
)

print("\n=== PLAUSIBILITÄTSPRÜFUNG ===")
print(f"Zeilen mit negativen Metrikwerten: {negative_values.sum()}")
print(f"Vollständig auswertbare Messungen: {valid_rows.sum()}")
print(f"Nicht vollständig auswertbare Messungen: {(~valid_rows).sum()}")

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
    and not negative_values.any()
)

print("\n=== GESAMTERGEBNIS ===")

if all_correct:
    print("Die HTML-Metrikdatei ist vollständig und plausibel.")
else:
    print("Die HTML-Metrikdatei enthält Auffälligkeiten.")

if not missing_websites.empty:
    print("\nBeispiele fehlender Webseiten:")
    print(missing_websites.head(20).to_string(index=False))

if metric_duplicates.any():
    print("\nBeispiele mehrfach vorhandener Webseiten:")
    print(
        metrics_df.loc[metric_duplicates, KEY_COLUMNS]
        .head(20)
        .to_string(index=False)
    )

if found_without_metrics.any():
    print("\nBeispiele mit found=True, aber fehlenden Metriken:")
    print(
        metrics_df.loc[
            found_without_metrics,
            KEY_COLUMNS + ["crawl_id"]
        ].head(20).to_string(index=False)
    )