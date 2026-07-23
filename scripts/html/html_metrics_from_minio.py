import re
import pandas as pd
from minio import Minio
from minio.error import S3Error
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import clickhouse_connect
import os

# Dateien
INPUT_FILE = "../../websites/top100_websites.csv"
OUTPUT_FILE = "../../csv/html_metrics.csv"
DATABASE = os.getenv("CLICKHOUSE_DATABASE", 'browser-crawler')
TABLE_CRAWLS = os.getenv("CLICKHOUSE_TABLE_CRAWLS", 'crawls')
CRAWL_TAG = os.getenv("CRAWL_TAG", "ba-dominik-uhl")
CRAWL_TAGS = os.getenv("CRAWL_TAGS", "ba-dominik-uhl,crux").split(",")

# MinIO-Client
BUCKET_NAME = "crawler-dom"

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
    query = """
    SELECT crawl_id
    FROM {database:Identifier}.{table:Identifier}
    WHERE url = {url:String}
    AND (has(tags, {tag:String}))
    AND dom_size != -1
    ORDER BY created_at DESC
    LIMIT 1
    """

    result = CLICKHOUSE_CLIENT.query(query, parameters={
        "url": url,
        "database": DATABASE,
        "table": TABLE_CRAWLS,
        "tag": CRAWL_TAG
    })

    if result.result_rows:
        crawl_id = str(result.result_rows[0][0])
        print(f"  Crawl-ID gefunden: {crawl_id}")
        return crawl_id

    print("  Keine passende Crawl-ID gefunden.")
    return None

# Alle Crawl-IDs suchen
def find_all_crawl_ids(url):

    query = """
    SELECT crawl_id
    FROM {database:Identifier}.{table:Identifier}
    WHERE url = {url:String}
    AND (hasAny(tags, {tags:Array(String)}))
    AND dom_size != -1
    ORDER BY created_at DESC
    """

    result = CLICKHOUSE_CLIENT.query(query,parameters={
        "url": url,
        "tags": CRAWL_TAGS,
        "database": DATABASE,
        "table": TABLE_CRAWLS
    })

    crawl_ids = []

    for crawl_id in result.result_rows:
        crawl_ids.append(str(crawl_id[0]))

    print(f"  {len(crawl_ids)} mögliche Crawl-IDs gefunden.")

    return crawl_ids

# Dateinamen erzeugen
def build_versioned_object_names(url):
    print(f"  Suche nach Pfaden für: {url}")
    domain = normalize_url(url)

    return [
        f"https/{domain}.html",
        f"http/{domain}.html",
    ]


# Metadatenwert aus Dictionary holen
def get_metadata_value(metadata, searched_key):
    searched_key = searched_key.lower()

    for key, value in metadata.items():
        if key.lower() == searched_key:
            return value

    return None


# HTML laden
def read_html_from_minio(object_name, version_id=None):
    response = MINIO_CLIENT.get_object(BUCKET_NAME, object_name, version_id=version_id)

    try:
        data = response.read()
    finally:
        response.close()
        response.release_conn()

    return data.decode("utf-8", errors="ignore"), len(data)

# Alle alten Objektpfade prüfen
def find_html(url, crawl_id):
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

                # Crawl-ID aus den Metadaten abrufen
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
                    # Passende Version gefunden
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

# Vorhandenen CSV-Eintrag aktualisieren
def update_result(result):
    output_df = pd.read_csv(OUTPUT_FILE)

    website = str(result["website"])

    website_mask = (
        output_df["website"]
        .astype(str)
        .eq(website)
    )

    if website_mask.any():
        for column, value in result.items():
            output_df.loc[website_mask, column] = value
    else:
        output_df = pd.concat(
            [output_df, pd.DataFrame([result])],
            ignore_index=True
        )

    # Nach jeder bearbeiteten Webseite speichern
    output_df.to_csv(
        OUTPUT_FILE,
        index=False
    )

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

# HTML Metriken berechnen
def calculate_metrics(html, html_size):
    soup = BeautifulSoup(html, "html.parser")

    text = soup.get_text(" ", strip=True)
    words = re.findall(r"\b\w+\b", text)

    return {
        "dom_size": html_size,
        "links": len(soup.find_all("a")),
        "images": len(soup.find_all("img")),
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
    print(f"[{index + 1}/{len(df)}] {website}")

    # Bereits gespeicherte Webseite überspringen
    if website in processed_websites:
        print("  Bereits bearbeitet. Wird übersprungen.")
        continue

    # 1. Crawl-ID aus ClickHouse
    crawl_id = find_crawl_id(website)

    if crawl_id is None:
        result ={
            "continent": continent,
            "country": country,
            "website": website,
            "crawl_id": None,
            "found": False
        }
        save_result(result)
        processed_websites.add(website)
        continue

    # 2. Passendes HTML suchen
    found_object = find_html(website, crawl_id)

    if found_object is None:
        print(f"  Kein passendes HTML für Crawl-ID {crawl_id} gefunden.")

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

    html = found_object["html"]
    html_size = found_object["html_size"]

    # 3. Metriken berechnen
    metrics = calculate_metrics(html, html_size)

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

# Nachsuche für nicht gefundene Webseiten
if os.path.exists(OUTPUT_FILE):
    output_df = pd.read_csv(OUTPUT_FILE)
    not_found_df = output_df[output_df["found"] == False].copy()

    total_not_found = len(not_found_df)

    print(
        f"{total_not_found} nicht gefundene Webseiten werden erneut geprüft."
    )

    for position, (_, row) in enumerate(not_found_df.iterrows(),start=1):
        continent = row["continent"]
        country = row["country"]
        website = row["website"]

        old_crawl_id = row.get("crawl_id")

        print("\n" + "=" * 80)
        print(
            f"[Nachsuche {position}/{total_not_found}] "
            f"{website}"
        )

        # Alle Crawls abrufen
        crawl_ids = find_all_crawl_ids(website)

        if not crawl_ids:
            print("  Keine weiteren Crawls gefunden.")
            continue

        matching_object = None
        matching_crawl_id = None

        # Crawls vom neuesten zum ältesten prüfen
        for crawl_id in crawl_ids:
            # Die bereits erfolglos geprüfte Crawl-ID überspringen
            if (
                pd.notna(old_crawl_id)
                and str(old_crawl_id) == str(crawl_id)
            ):
                print(
                    f"Crawl {crawl_id} wurde bereits geprüft."
                )
                continue
            # Passendes HTML suchen
            found_object = find_html(
                website,
                crawl_id
            )

            if found_object is not None:
                matching_object = found_object
                matching_crawl_id = crawl_id
                break

            print(
                f"  Kein HTML für Crawl-ID "
                f"{crawl_id} gefunden."
            )

        if matching_object is None:
            print(
                "  Auch mit älteren BA-/CrUX-Crawls "
                "wurde kein passendes HTML gefunden."
            )
            continue

        # Metriken aus der gefundenen HTML-Version berechnen
        metrics = calculate_metrics(
            matching_object["html"],
            matching_object["html_size"]
        )

        result = {
            "continent": continent,
            "country": country,
            "website": website,
            "crawl_id": matching_crawl_id,
            "found": True,
            **metrics
        }

        # Bestehenden False-Eintrag aktualisieren
        update_result(result)

        print(
            f"  Erfolgreich mit Crawl-ID "
            f"{matching_crawl_id}."
        )
        print(f"  Metriken berechnet: {metrics}")

print(f"Fertig: {OUTPUT_FILE}")