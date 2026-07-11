import os
import warnings
import pandas as pd
import requests
import tldextract
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
from langdetect import detect

# Warnungen für BeautifulSoup unterdrücken
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

# Dateien
COUNTRIES_FILE = "../../countries/country_selection.csv"
EXISTING_FILE = "../../websites/top100_websites.csv"
OUTPUT_FILE = "../../websites/top100_websites.csv"

CRUX_FILES = [
    "../../crux/202605_fj.csv",
    "../../crux/202605_pf.csv",
    "../../crux/202605_nc.csv",
    "../../crux/202605_ni.csv",
    "../../crux/202605_pw.csv",
    "../../crux/202605_pg.csv",
    "../../crux/202605_sn.csv",
]

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
            return html["lang"].split("-")[0].lower()
    
        # 2. Prüfen, ob genügend Text vorhanden ist, um die Sprache zu erkennen
        text = soup.get_text(" ", strip=True)
        if len(text) > 200:
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

# CSV-Dateien einlesen
countries = pd.read_csv(COUNTRIES_FILE, sep=None, engine="python", encoding="utf-8-sig")
existing = pd.read_csv(EXISTING_FILE)

results = existing.to_dict("records")

global_existing_websites = set(existing["website"])

# Alle Länder durchgehen
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

    # Wenn bereits genügend Webseiten vorhanden sind, überspringen
    if current_count >= TOP_N:
        print("  already complete")
        continue

    needed = TOP_N - current_count

    country_added = []

    # Alle CrUX-Dateien durchgehen
    for crux_file in CRUX_FILES:
        if needed <= 0:
            break
        # Nur die CrUX-Dateien prüfen, die zur ccTLD passen
        if f"_{cctld[1:]}" not in os.path.basename(crux_file):
            continue
        print(f"  checking {crux_file}")

        crux = pd.read_csv(crux_file, usecols=["origin", "rank"])
        crux = crux.sort_values("rank")

        candidates = crux[
            crux["origin"].apply(get_cctld) == cctld
        ].copy()

        print(f"    ccTLD candidates: {len(candidates)}")

        # Sprache prüfen und hinzufügen
        for _, row in candidates.iterrows():
            if needed <= 0:
                break

            origin = row["origin"]

            if origin in global_existing_websites:
                continue
            
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

# Ergebnisse in DataFrame umwandeln und speichern
output = pd.DataFrame(results)
output = output[["continent", "country", "website"]]

os.makedirs("../websites", exist_ok=True)
output.to_csv(OUTPUT_FILE, index=False)

print()
print("Finished")
print(f"Rows: {len(output)}")
print(f"Saved to {OUTPUT_FILE}")