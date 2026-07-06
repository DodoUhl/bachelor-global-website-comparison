import os
import re
import csv
import pandas as pd
from minio import Minio
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from collections import deque

# Dateien
INPUT_FILE = "../websites/top100_websites.csv"
OUTPUT_FILE = "../websites/top100_websites_metrics.csv"

BUCKET_NAME = "crawler-screenshots"

client = Minio(
    "s3.vs.uni-kassel.de",
    access_key="duhl",
    secret_key="norxot-Xypva6-byrguc",
    secure=False
)


def normalize_url(url):
    url = str(url).strip().rstrip(".")
    parsed = urlparse(url)

    domain = parsed.netloc.lower()
    scheme = parsed.scheme.lower()

    if domain.startswith("www."):
        domain_without_www = domain[4:]
    else:
        domain_without_www = domain

    return scheme, domain, domain_without_www


def find_dom_object(website):
    scheme, domain, domain_without_www = normalize_url(website)

    candidates = [
        f"{scheme}/{domain}.html",
        f"{scheme}/{domain_without_www}.html",
        f"http/{domain}.html",
        f"http/{domain_without_www}.html",
        f"https/{domain}.html",
        f"https/{domain_without_www}.html",
    ]
    
    print(f"  Searching for DOM object for {website} with candidates: {candidates}")
    # MinIO-Struktur: crawls/<crawl_id>/<scheme>/<domain>.html
    for obj in client.list_objects(BUCKET_NAME, recursive=True):
        object_name = obj.object_name
        print(f"  Checking {object_name} against candidate {candidate}")
        for candidate in candidates: 
            if object_name.endswith(candidate): 
                return object_name

    return None


def read_html_from_minio(object_name):
    response = client.get_object(BUCKET_NAME, object_name)

    try:
        html = response.read().decode("utf-8", errors="ignore")
    finally:
        response.close()
        response.release_conn()

    return html


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


def main():
    df = pd.read_csv(INPUT_FILE)

    results = []

    for index, row in df.iterrows():
        continent = row["continent"]
        country = row["country"]
        website = row["website"]

        print(f"[{index + 1}/{len(df)}] Suche DOM für {website}")

        object_name = find_dom_object(website)

        if object_name is None:
            print(f"  Nicht gefunden: {website}")

            results.append({
                "continent": continent,
                "country": country,
                "website": website,
                "dom_object": "",
                "found": False,
                "dom_size": "",
                "dom_depth": "",
                "links": "",
                "images": "",
                "forms": "",
                "tables": "",
                "buttons": "",
                "text_chars": "",
                "text_words": "",
                "text_blocks": "",
            })

            continue

        print(f"  Gefunden: {object_name}")

        html = read_html_from_minio(object_name)
        metrics = calculate_metrics(html)

        results.append({
            "continent": continent,
            "country": country,
            "website": website,
            "dom_object": object_name,
            "found": True,
            **metrics
        })

    output_df = pd.DataFrame(results)
    output_df.to_csv(OUTPUT_FILE, index=False)

    print(f"\nFertig. Ergebnis gespeichert unter: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()