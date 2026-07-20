import pandas as pd
import clickhouse_connect
import os

# Dateien
INPUT_FILE = "../../websites/top100_websites.csv"
OUTPUT_FILE = "../../csv/har_metrics.csv"

# ClickHouse
CLICKHOUSE_CLIENT = clickhouse_connect.get_client(
    host="bithouse1.vs.uni-kassel.de",
    port=443,
    username="duhl",
    password="CvJg2Ac6cHxwucKz",
    secure=True,
    verify=False
)

# Crawl-ID suchen
def find_crawl_id(url):
    query = f"""
    SELECT crawl_id
    FROM "browser-crawler"."crawls"
    WHERE url = '{url}'
    AND has(tags, 'ba-dominik-uhl')
    ORDER BY created_at DESC
    LIMIT 1
    """

    result = CLICKHOUSE_CLIENT.query(query)

    if result.result_rows:
        crawl_id = str(result.result_rows[0][0])
        print(f"  Crawl-ID gefunden: {crawl_id}")
        return crawl_id

    print("  Keine passende Crawl-ID gefunden.")
    return None

# Metriken aus HAR-Einträgen berechnen
def analyze_har(crawl_id):
    query = f"""
    SELECT
    entry_id,
    request_url,
    response_content_type,
    response_content_size
    FROM "browser-crawler"."har_entries"
    WHERE crawl_id = '{crawl_id}'
    """

    result = CLICKHOUSE_CLIENT.query(query)

    if len(result.result_rows) == 0:
        return None

    df = pd.DataFrame(
        result.result_rows,
        columns=[
            "entry_id",
            "request_url",
            "content_type",
            "content_size"
        ]
    )

    # Negative Größen auf 0 setzen
    df["content_size"] = df["content_size"].clip(lower=0)

    metrics = {
        "num_requests": len(df),
        "html": 0,
        "css": 0,
        "javascript": 0,
        "images": 0,
        "fonts": 0,
        "transferred_bytes": int(df["content_size"].sum())
    }

    for ct in df["content_type"].fillna("").str.lower():

        if "text/html" in ct:
            metrics["html"] += 1

        elif "text/css" in ct:
            metrics["css"] += 1

        elif "javascript" in ct or "ecmascript" in ct:
            metrics["javascript"] += 1

        elif ct.startswith("image/"):
            metrics["images"] += 1

        elif "font" in ct or "woff" in ct or "ttf" in ct or "otf" in ct:
            metrics["fonts"] += 1

    return metrics

# Ergebnisse speichern
def save_result(result):
    result_df = pd.DataFrame([result])

    file_exists = os.path.exists(OUTPUT_FILE)

    result_df.to_csv(
        OUTPUT_FILE,
        mode="a",
        header=not file_exists,
        index=False
    )

# CSV einlesen
df = pd.read_csv(INPUT_FILE, sep=None, engine="python")

processed_websites = set()

if os.path.exists(OUTPUT_FILE):
    existing_df = pd.read_csv(OUTPUT_FILE)

    if "website" in existing_df.columns:
        processed_websites = set(
            existing_df["website"]
            .dropna()
            .astype(str)
        )

for index, row in df.iterrows():
    continent = row["continent"]
    country = row["country"]
    website = row["website"]

    print("\n" + "=" * 80)
    print(f"[{index+1}/{len(df)}] {website}")

    # Bereits gespeicherte Webseite überspringen
    if website in processed_websites:
        print("  Bereits bearbeitet. Wird übersprungen.")
        continue

    # 1. Crawl-ID aus ClickHouse
    crawl_id = find_crawl_id(website)

    if crawl_id is None:
        result = {
            "continent": continent,
            "country": country,
            "website": website,
            "crawl_id": None,
            "found": False
        }
        save_result(result)
        processed_websites.add(website)
        continue

    # 2. Metriken berechnen
    metrics = analyze_har(crawl_id)

    if metrics is None:
        print("  -> Keine HAR-Einträge gefunden")
        result = {
            "continent": continent,
            "country": country,
            "website": website,
            "crawl_id": crawl_id,
            "found": False
        }
        save_result(result)
        processed_websites.add(website)
        continue

    result = {
        "continent": continent,
        "country": country,
        "website": website,
        "crawl_id": crawl_id,
        "found": True,
        **metrics
    }
    save_result(result)
    processed_websites.add(website)
    print(f"  Metriken berechnet: {metrics}")

print(f"\nFertig: {OUTPUT_FILE}")