import re
import pandas as pd
from minio import Minio
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from collections import deque
import clickhouse_connect

# Dateien
INPUT_FILE = "../websites/top100_websites.csv"
OUTPUT_FILE = "../websites/html_metrics.csv"

# Minio-Client
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

# url normalisieren nach scheme und domain
def normalize_url(url):
    url = str(url).strip().rstrip("/")

    parsed = urlparse(url)

    scheme = parsed.scheme.lower()
    domain = parsed.netloc.lower()

    if domain.startswith("www."):
        domain = domain[4:]

    return scheme, domain

# crawl_id suchen
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

# Dateiname aus URL und crawl_id bauen
def build_object_names(url, crawl_id):
    scheme, domain = normalize_url(url)
    names = []
    if crawl_id is not None:
        names.append(f"crawls/{crawl_id}/https/{domain}.html")
        names.append(f"crawls/{crawl_id}/http/{domain}.html")
        names.append(f"crawls/{crawl_id}/https/www.{domain}.html")
        names.append(f"crawls/{crawl_id}/http/www.{domain}.html")

    names.append(f"crawls/https/www.{domain}.html")
    names.append(f"crawls/https/{domain}.html")
    names.append(f"crawls/http/www.{domain}.html")
    names.append(f"crawls/http/{domain}.html")

    return list(dict.fromkeys(names))

#HTML aus Minio laden
def read_html_from_minio(object_name):
    response = MINIO_CLIENT.get_object(BUCKET_NAME, object_name)

    try:
        html = response.read().decode("utf-8", errors="ignore")
    finally:
        response.close()
        response.release_conn()

    return html

# DOM-Tiefe berechnen
def calculate_dom_depth(soup):
    max_depth = 0

    queue = deque([(soup, 0)])

    while queue:
        node, depth = queue.popleft()
        max_depth = max(max_depth, depth)

        for child in getattr(node, "children", []):
            if getattr(child, "name", None):
                queue.append((child, depth + 1))

    return max_depth

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

# Alle Metriken berechnen
def calculate_metrics(html):
    soup = BeautifulSoup(html, "html.parser")

    text = soup.get_text(" ", strip=True)
    words = re.findall(r"\b\w+\b", text)

    metrics = {
        "dom_size": len(soup.find_all()),
        "dom_depth": calculate_dom_depth(soup),
        "links": len(soup.find_all("a")),
        "images": len(soup.find_all("img")),
        "forms": len(soup.find_all("form")),
        "tables": len(soup.find_all("table")),
        "buttons": len(soup.find_all("button")) + len(soup.find_all("input", {"type": "button"})) + len(soup.find_all("input", {"type": "submit"})),
        "text_chars": len(text),
        "text_words": len(words),
        "text_blocks": count_text_blocks(soup),
    }

    return metrics

# Alle Webseiten aus der CSV-Datei einlesen
df = pd.read_csv(INPUT_FILE, sep=None, engine="python")

results = []

# Alle Webseiten durchgehen
for index, row in df.iterrows():

    continent = row["continent"]
    country = row["country"]
    website = row["website"]

    print(f"[{index+1}/{len(df)}] {website}")

    # 1. crawl_id suchen
    crawl_id = find_crawl_id(website)

    # 2. Object Name bauen
    object_names = build_object_names(website, crawl_id)

    print(f"  Object: {object_names}")

    # 3. HTML holen
    html = None
    for object_name in object_names:
        print(f"  Versuche: {object_name}")
        try:
            html = read_html_from_minio(object_name)
            print(f"  HTML gefunden: {object_name}")
            break
        except Exception:
            pass
    
    if html is None:
        print(f"  HTML nicht gefunden für: {website}")
        results.append({
            "continent": continent,
            "country": country,
            "website": website,
            "found": False
        })
        continue

    # 4. Metriken
    metrics = calculate_metrics(html)
    
    results.append({
        "continent": continent,
        "country": country,
        "website": website,
        "found": True,
        **metrics
})

# Ergebnisse in DataFrame umwandeln und speichern
output_df = pd.DataFrame(results)
output_df.to_csv(OUTPUT_FILE, index=False)

print(f"\nFertig: {OUTPUT_FILE}")
