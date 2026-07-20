import re
import pandas as pd
from minio import Minio
from minio.error import S3Error
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import clickhouse_connect

# Dateien
INPUT_FILE = "../../websites/top100_websites.csv"
OUTPUT_FILE = "../../csv/html_metrics.csv"

# MinIO-Client
BUCKET_NAME = "crawler-dom"
MINIO_CLIENT = Minio(
    "s3.vs.uni-kassel.de",
    access_key="duhl",
    secret_key="norxot-Xypva6-byrguc",
    secure=True
)

# ClickHouse-Client
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


# Neuste passende Crawl-ID aus ClickHouse suchen
def find_crawl_id(url):
    query = """
    SELECT crawl_id
    FROM "browser-crawler"."crawls"
    WHERE url = '{url}'
    AND has(tags, 'ba-dominik-uhl')
    AND dom_size != -1
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
        f"https/{domain}.html",
        f"http/{domain}.html",
    ]


# Metadatum unabhängig von Groß-/Kleinschreibung lesen
def get_metadata_value(metadata, searched_key):
    searched_key = searched_key.lower()

    for key, value in metadata.items():
        if key.lower() == searched_key:
            return value

    return None


# HTML aus einer bestimmten Objektversion laden
def read_html_from_minio(object_name, version_id=None):
    response = MINIO_CLIENT.get_object(BUCKET_NAME, object_name, version_id=version_id)

    try:
        content = response.read()
        return content.decode("utf-8", errors="ignore"), len(content)
    finally:
        response.close()
        response.release_conn()


# Bei alten Pfaden die Version mit passender Crawl-ID suchen
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
                    html, html_size = read_html_from_minio(
                        object_name,
                        version_id=version.version_id
                    )
                    html_size = stat.size
                    print("  Passende MinIO-Version gefunden.")

                    return {
                        "html": html,
                        "html_size": html_size
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


# Alle alten Objektpfade prüfen
def find_html(url, crawl_id):
    object_names = build_versioned_object_names(url)

    for object_name in object_names:
        result = find_matching_version(object_name, crawl_id)

        if result is not None:
            return result

    return None

# Textblöcke zählen
def count_text_blocks(soup):
    block_tags = [
        "p", "div", "section", "article", "main", "aside",
        "header", "footer", "li", "td", "th", "blockquote"
    ]

    count = 0

    for tag in soup.find_all(block_tags):
        text = tag.get_text(" ", strip=True)

        if len(text) >= 30:
            count += 1

    return count


# Metriken berechnen
def calculate_metrics(html, html_size):
    soup = BeautifulSoup(html, "html.parser")

    text = soup.get_text(" ", strip=True)
    words = re.findall(r"\b\w+\b", text)

    return {
        "dom_size": html_size,
        "links": len(soup.find_all("a")),
        "images": len(soup.find_all("img")), # Oder response_content_type LIKE 'image/%'
        "forms": len(soup.find_all("form")),
        "tables": len(soup.find_all("table")),
        "buttons": (
            len(soup.find_all("button"))
            + len(soup.find_all("input", {"type": "button"}))
            + len(soup.find_all("input", {"type": "submit"}))
        ),
        "text_chars": len(text),
        "text_words": len(words),
        "text_blocks": count_text_blocks(soup),
    }

df = pd.read_csv(INPUT_FILE, sep=None, engine="python")

results = []

for index, row in df.iterrows():
    continent = row["continent"]
    country = row["country"]
    website = row["website"]

    print("\n" + "=" * 80)
    print(f"[{index + 1}/{len(df)}] {website}")

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

    # 2. Passendes HTML suchen
    found_object = find_html(website, crawl_id)

    if found_object is None:
        print(f"  Kein passendes HTML für Crawl-ID {crawl_id} gefunden.")

        results.append({
            "continent": continent,
            "country": country,
            "website": website,
            "crawl_id": crawl_id,
            "found": False
        })
        continue

    html = found_object["html"]
    html_size = found_object["html_size"]

    # 3. Metriken berechnen
    metrics = calculate_metrics(html, html_size)

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

print("\n" + "=" * 80)
print(f"Fertig: {OUTPUT_FILE}")