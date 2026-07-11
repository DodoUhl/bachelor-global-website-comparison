import io
import pandas as pd
from PIL import Image
from minio import Minio
from urllib.parse import urlparse
import clickhouse_connect

# Dateien
INPUT_FILE = "../websites/top100_websites.csv"
OUTPUT_FILE = "../websites/visually_metrics.csv"

# Minio
BUCKET_NAME = "crawler-screenshots"

MINIO_CLIENT = Minio(
    "s3.vs.uni-kassel.de",
    access_key="duhl",
    secret_key="norxot-Xypva6-byrguc",
    secure=True
)

# ClickHouse
CLICKHOUSE_CLIENT = clickhouse_connect.get_client(
    host="bithouse1.vs.uni-kassel.de",
    port=443,
    username="duhl",
    password="CvJg2Ac6cHxwucKz",
    secure=True,
    verify=False
)

# URL normalisieren
def normalize_url(url):
    url = str(url).strip().rstrip("/")

    parsed = urlparse(url)

    scheme = parsed.scheme.lower()
    domain = parsed.netloc.lower()

    if domain.startswith("www."):
        domain = domain[4:]

    return scheme, domain

# Crawl-ID suchen
def find_crawl_id(url):
    query = f"""
    SELECT crawl_id
    FROM "browser-crawler"."crawls"
    WHERE url = '{url}'
    AND dom_size != -1
    ORDER BY created_at DESC
    LIMIT 1
    """

    result = CLICKHOUSE_CLIENT.query(query)

    if result.result_rows:
        print(f"  Crawl ID gefunden: {result.result_rows[0][0]}")
        return result.result_rows[0][0]

    return None

# Dateinamen erzeugen
def build_object_names(url, crawl_id):
    scheme, domain = normalize_url(url)

    names = []

    if crawl_id is not None:
        names.append(f"crawls/{crawl_id}/https/{domain}.png")
        names.append(f"crawls/{crawl_id}/http/{domain}.png")
        names.append(f"crawls/{crawl_id}/https/www.{domain}.png")
        names.append(f"crawls/{crawl_id}/http/www.{domain}.png")

    names.append(f"crawls/https/www.{domain}.png")
    names.append(f"crawls/https/{domain}.png")
    names.append(f"crawls/http/www.{domain}.png")
    names.append(f"crawls/http/{domain}.png")

    return list(dict.fromkeys(names))

# Screenshot laden
def read_screenshot(object_name):
    response = MINIO_CLIENT.get_object(BUCKET_NAME, object_name)

    try:
        image = Image.open(io.BytesIO(response.read()))
        image.load()
    finally:
        response.close()
        response.release_conn()

    return image

# Screenshotmetriken
def calculate_metrics(image):
    width, height = image.size

    metrics = {
        "width": width,
        "height": height,
        "pixel_count": width * height,
        "aspect_ratio": round(width / height, 4) if height else None
    }

    return metrics

# CSV einlesen
df = pd.read_csv(INPUT_FILE, sep=None, engine="python")

results = []

for index, row in df.iterrows():

    continent = row["continent"]
    country = row["country"]
    website = row["website"]

    print(f"[{index+1}/{len(df)}] {website}")

    crawl_id = find_crawl_id(website)

    object_names = build_object_names(website, crawl_id)

    image = None

    for object_name in object_names:
        print(f"  Versuche: {object_name}")
        try:
            image = read_screenshot(object_name)
            print(f"  Screenshot gefunden")
            break
        except Exception:
            pass

    if image is None:
        print("  Screenshot nicht gefunden")

        results.append({
            "continent": continent,
            "country": country,
            "website": website,
            "found": False
        })

        continue

    metrics = calculate_metrics(image)

    results.append({
        "continent": continent,
        "country": country,
        "website": website,
        "found": True,
        **metrics
    })

output_df = pd.DataFrame(results)
output_df.to_csv(OUTPUT_FILE, index=False)

print(f"\nFertig: {OUTPUT_FILE}")