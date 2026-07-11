import pandas as pd
import clickhouse_connect

# Dateien
INPUT_FILE = "../websites/top100_websites.csv"
OUTPUT_FILE = "../websites/network_metrics.csv"

# ClickHouse-Client
CLICKHOUSE_CLIENT = clickhouse_connect.get_client(
    host="bithouse1.vs.uni-kassel.de",
    port=443,
    username="duhl",
    password="CvJg2Ac6cHxwucKz",
    secure=True,
    verify=False
)


def get_latest_crawl_id(url):
    query = f"""
    SELECT crawl_id
    FROM "browser-crawler"."crawls"
    WHERE url = '{url}'
      AND dom_size != -1
    ORDER BY created_at DESC
    LIMIT 1
    """

    result = CLICKHOUSE_CLIENT.query(query)

    if len(result.result_rows) == 0:
        return None

    return result.result_rows[0][0]


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

websites = pd.read_csv(INPUT_FILE)

results = []

for _, row in websites.iterrows():
    url = row["website"]

    print(url)

    crawl_id = get_latest_crawl_id(url)

    if crawl_id is None:
        print("  -> Kein Crawl gefunden")
        continue

    metrics = analyze_har(crawl_id)

    if metrics is None:
        print("  -> Keine HAR-Einträge gefunden")
        continue

    results.append({
        "continent": row["continent"],
        "country": row["country"],
        "website": url,
        **metrics
    })

pd.DataFrame(results).to_csv(OUTPUT_FILE, index=False)

print(f"Gespeichert unter {OUTPUT_FILE}")