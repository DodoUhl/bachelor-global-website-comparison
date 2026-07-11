import io
import cv2
import numpy as np
from sklearn.cluster import KMeans
from scipy.stats import entropy
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
        data = response.read()
    finally:
        response.close()
        response.release_conn()

    image = Image.open(io.BytesIO(data)).convert("RGB")

    return image, len(data)

# Screenshotmetriken
def calculate_metrics(image, file_size):

    rgb = np.array(image)

    height, width = rgb.shape[:2]

    # Screenshot-Höhe
    screenshot_height = height

    # Unique Colors
    unique_colors = len(np.unique(rgb.reshape(-1, 3), axis=0))

    # HSV
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)

    saturation = hsv[:, :, 1]
    brightness = hsv[:, :, 2]

    avg_saturation = float(np.mean(saturation))
    avg_brightness = float(np.mean(brightness))

    # Weißraum, Pixel mit sehr hoher Helligkeit und geringer Sättigung
    white_pixels = np.logical_and(
        brightness > 245,
        saturation < 15
    )

    whitespace_ratio = white_pixels.mean()

    # Color Entropy
    pixels = rgb.reshape(-1, 3)

    _, counts = np.unique(pixels, axis=0, return_counts=True)

    probabilities = counts / counts.sum()

    color_entropy = entropy(probabilities, base=2)

    # Dominante Farben (KMeans)
    sample_size = min(10000, len(pixels))

    idx = np.random.choice(len(pixels), sample_size, replace=False)

    sample = pixels[idx]

    kmeans = KMeans(
        n_clusters=5,
        random_state=42,
        n_init="auto"
    ).fit(sample)

    dominant_colors = kmeans.cluster_centers_.astype(int)

    metrics = {
        "dominant_color_1": tuple(dominant_colors[0]),
        "dominant_color_2": tuple(dominant_colors[1]),
        "dominant_color_3": tuple(dominant_colors[2]),
        "dominant_color_4": tuple(dominant_colors[3]),
        "dominant_color_5": tuple(dominant_colors[4]),
        "unique_colors": unique_colors,
        "color_entropy": color_entropy,
        "average_saturation": avg_saturation,
        "average_brightness": avg_brightness,
        "whitespace_ratio": whitespace_ratio,
        "screenshot_height": screenshot_height,
        "screenshot_file_size": file_size
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
            image, file_size = read_screenshot(object_name)
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

    metrics = calculate_metrics(image, file_size)

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