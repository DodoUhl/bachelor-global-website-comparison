import io
from minio.error import S3Error
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
INPUT_FILE = "../../websites/top100_websites.csv"
OUTPUT_FILE = "../../websites/visually_metrics.csv"

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

    return domain

# Crawl-ID suchen
def find_crawl_id(url):
    query = f"""
    SELECT crawl_id
    FROM "browser-crawler"."crawls"
    WHERE url = '{url}'
    AND screenshot_full_size != -1
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

# Dateinamen erzeugen
def build_versioned_object_names(url):
    print(f"  Suche nach Pfaden für: {url}")
    domain = normalize_url(url)

    return [
        f"https/{domain}.full.png",
        f"http/{domain}.full.png",
    ]

# Metadatum unabhängig von Groß-/Kleinschreibung lesen
def get_metadata_value(metadata, searched_key):
    searched_key = searched_key.lower()

    for key, value in metadata.items():
        if key.lower() == searched_key:
            return value

    return None

# Screenshot laden
def read_screenshot_from_minio(object_name, version_id=None):
    response = MINIO_CLIENT.get_object(BUCKET_NAME, object_name, version_id=version_id)

    try:
        data = response.read()
    finally:
        response.close()
        response.release_conn()

    image = Image.open(io.BytesIO(data)).convert("RGB")

    return image, len(data)

# Alle alten Objektpfade prüfen
def find_screenshot(url, crawl_id):
    object_names = build_versioned_object_names(url)

    for object_name in object_names:
        result = find_matching_version(object_name, crawl_id)

        if result is not None:
            return result

    return None

# Die Version mit passender Crawl-ID suchen
def find_matching_version(object_name, crawl_id):
    print(f"  Durchsuche Versionen von: {object_name}")

    try:
        versions = MINIO_CLIENT.list_objects(
            BUCKET_NAME,
            prefix=object_name,
            recursive=True,
            include_version=True
        )

        for version in versions:
            # Prefix-Suche kann auch andere Objekte liefern
            if version.object_name != object_name:
                continue

            # Delete Marker überspringen
            if getattr(version, "is_delete_marker", False):
                continue

            try:
                stat = MINIO_CLIENT.stat_object(
                    BUCKET_NAME,
                    object_name,
                    version_id=version.version_id
                )

                metadata_crawl_id = get_metadata_value(
                    stat.metadata,
                    "x-amz-meta-crawl-id"
                )

                print(
                    f"    Version: {version.version_id} | "
                    f"Datum: {version.last_modified} | "
                    f"Crawl-ID: {metadata_crawl_id}"
                )

                if (
                    metadata_crawl_id is not None
                    and str(metadata_crawl_id) == str(crawl_id)
                ):
                    image, image_size = read_screenshot_from_minio(
                        object_name,
                        version_id=version.version_id
                    )
                    image_size = stat.size
                    print("  Passende MinIO-Version gefunden.")

                    return {
                        "image": image,
                        "image_size": image_size
                    }

            except S3Error as error:
                print(
                    f"    Version {version.version_id} "
                    f"konnte nicht geprüft werden: {error}"
                )

            except Exception as error:
                print(
                    f"    Fehler bei Version {version.version_id}: {error}"
                )

    except S3Error as error:
        if error.code not in {"NoSuchKey", "NoSuchObject"}:
            print(f"  Fehler beim Auflisten der Versionen: {error}")

    except Exception as error:
        print(f"  Fehler beim Auflisten der Versionen: {error}")

    return None

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

    print("\n" + "=" * 80)
    print(f"[{index+1}/{len(df)}] {website}")

    # 1. Crawl-ID aus ClickHouse
    crawl_id = find_crawl_id(website)

    if crawl_id is None:
        results.append({
            "continent": continent,
            "country": country,
            "website": website,
            "crawl_id": None,
            "found": False
        })
        continue

    # 2. Passendes Screenshot suchen
    found_object = find_screenshot(website, crawl_id)

    if found_object is None:
        print(f"  Kein passendes Screenshot für Crawl-ID {crawl_id} gefunden.")

        results.append({
            "continent": continent,
            "country": country,
            "website": website,
            "crawl_id": crawl_id,
            "found": False
        })
        continue

    image = found_object["image"]
    image_size = found_object["image_size"]

    # 3. Metriken berechnen
    metrics = calculate_metrics(image, image_size)

    results.append({
        "continent": continent,
        "country": country,
        "website": website,
        "crawl_id": crawl_id,
        "found": True,
        **metrics
    })
    print(f"  Metriken berechnet: {metrics}")

output_df = pd.DataFrame(results)
output_df.to_csv(OUTPUT_FILE, index=False)

print(f"\nFertig: {OUTPUT_FILE}")