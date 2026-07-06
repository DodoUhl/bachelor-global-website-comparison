import os
import warnings
import pandas as pd
import requests
import tldextract
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
from langdetect import detect

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

COUNTRIES_FILE = "../countries/country_selection.csv"
EXISTING_FILE = "../websites/top100_websites.csv"
OUTPUT_FILE = "../websites/top100_websites.csv"

CRUX_FILES = [
    "../crux/202605.csv",
    "../crux/202604.csv",
    "../crux/202603.csv",
    "../crux/202602.csv",
    "../crux/202601.csv",
    "../crux/202512.csv",
    "../crux/202511.csv",
    "../crux/202510.csv",
    "../crux/202509.csv",
    "../crux/202508.csv",
    "../crux/202507.csv",
    "../crux/202506.csv",
    "../crux/202505.csv",
    "../crux/202504.csv",
]
TRANCO_FILE = "../tranco/tranco_GQ2WK.csv.gz"

# Anzahl der Webseiten pro Land
TOP_N = 100

# TLD extrahieren
def get_cctld(origin):
    ext = tldextract.extract(origin)
    if not ext.suffix:
        return ""
    return "." + ext.suffix.split(".")[-1].lower()

# Sprache erkennen
def detect_language(origin):
    try:
        response = requests.get(
            origin,
            timeout=8,
            headers={"User-Agent": "Mozilla/5.0"}
        )

        soup = BeautifulSoup(response.text, "html.parser")

        html = soup.find("html")

        # 1. Prüfen, ob die Sprache im HTML-Tag angegeben ist
        if html and html.get("lang"):
            print(f"  detected language from HTML tag: {html['lang']}")
            return html["lang"].split("-")[0].lower()
    
        # 2. Prüfen, ob genügend Text vorhanden ist, um die Sprache zu erkennen
        text = soup.get_text(" ", strip=True)
        if len(text) > 200:
            print(f"  detected language from text: {detect(text)}")
            return detect(text)

    except Exception:
        return None

    return None

# Sprache normalisieren
def normalize_language(language):
    if language is None:
        return None
    language = language.lower().strip()
    language = language.replace("_", "-")
    
    return language.split("-")[0]


countries = pd.read_csv(COUNTRIES_FILE, sep=None, engine="python")
existing = pd.read_csv(EXISTING_FILE)

results = existing.to_dict("records")

global_existing_websites = set(existing["website"])

for _, country_row in countries.iterrows():
    continent = country_row["continent"]
    country = country_row["country"]
    print(f"\nProcessing {country} ({continent})")
    cctld = str(country_row["cctld"]).lower()

    languages = [
        lang.strip().lower()
        for lang in str(country_row["languages"]).split(",")
    ]

    current_count = len(existing[existing["country"] == country])

    print(f"\nProcessing {country}")
    print(f"  current websites: {current_count}")

    if current_count >= TOP_N:
        print("  already complete")
        continue

    needed = TOP_N - current_count

    country_added = []

    for crux_file in CRUX_FILES:
        if needed <= 0:
            break

        print(f"  checking {crux_file}")

        crux = pd.read_csv(crux_file, usecols=["origin", "rank"])
        crux = crux.sort_values("rank")

        candidates = crux[
            crux["origin"].apply(get_cctld) == cctld
        ].copy()

        print(f"    ccTLD candidates: {len(candidates)}")

        for _, row in candidates.iterrows():
            if needed <= 0:
                break

            origin = row["origin"]

            if origin in global_existing_websites:
                continue

            # Außer in Ozeanien Sprache prüfen
            if continent != "Oceania":
                language = normalize_language(detect_language(origin))
                if language not in languages:
                    continue

            item = {
                "continent": continent,
                "country": country,
                "website": origin,
            }

            results.append(item)
            country_added.append(item)
            global_existing_websites.add(origin)

            needed -= 1

        print(f"    added so far for {country}: {len(country_added)}")

    for tranco_file in [TRANCO_FILE]:
        if needed <= 0:
            break

        print(f"  checking {tranco_file}")

        tranco = pd.read_csv(tranco_file, compression="gzip", header=None, names=["rank", "domain"])
        tranco["domain"] = "https://" + tranco["domain"]

        candidates = tranco[
            tranco["domain"].apply(get_cctld) == cctld
        ].copy()

        candidates = candidates.sort_values("rank")

        print(f"    ccTLD candidates: {len(candidates)}")

        for _, row in candidates.iterrows():
            if needed <= 0:
                break

            origin = row["domain"]

            if origin in global_existing_websites:
                continue

            # Außer in Ozeanien Sprache prüfen
            if continent != "Oceania":
                language = normalize_language(detect_language(origin))

                if language not in languages:
                    continue

            item = {
                "continent": continent,
                "country": country,
                "website": origin,
            }

            results.append(item)
            country_added.append(item)
            global_existing_websites.add(origin)

            needed -= 1

        print(f"    added so far for {country}: {len(country_added)}")

    print(f"  final added: {len(country_added)}")
    print(f"  final count: {current_count + len(country_added)}")


output = pd.DataFrame(results)
output = output[["continent", "country", "website"]]

os.makedirs("../websites", exist_ok=True)
output.to_csv(OUTPUT_FILE, index=False)

print()
print("Finished")
print(f"Rows: {len(output)}")
print(f"Saved to {OUTPUT_FILE}")