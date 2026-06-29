import pandas as pd
import requests
import tldextract
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
from langdetect import detect
import warnings
import os

warnings.filterwarnings(
    "ignore",
    category=XMLParsedAsHTMLWarning
)

# Dateien
COUNTRIES_FILE = "../countries/country_selection.csv"
CRUX_FILE = "../crux/202605.csv"
OUTPUT_FILE = "../websites/top100_websites.csv"
OUTPUT_DIR = "../websites"

# Anzahl der Webseiten pro Land
TOP_N = 100

# TLD extrahieren
def get_cctld(origin):
    ext = tldextract.extract(origin)
    return "." + ext.suffix.lower() if ext.suffix else ""

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

# Speichern der Ergebnisse pro Kontinent
def save_continent_csv(continent, rows):
    if not rows:
        return

    filename = continent.lower().replace(" ", "_")
    path = os.path.join(OUTPUT_DIR, f"top100_websites_{filename}.csv")

    df = pd.DataFrame(rows)
    df = df[["continent", "country", "website"]]
    df.to_csv(path, index=False)

    print(f"Saved continent CSV: {path}")


countries = pd.read_csv(COUNTRIES_FILE)
crux = pd.read_csv(CRUX_FILE)

results = []

# Iteriere über alle Länder
for continent, continent_countries in countries.groupby("continent"):
    print(f"\nProcessing continent: {continent} ({len(continent_countries)} countries)")
    continent_results = []
    for _, country_row in continent_countries.iterrows():
        country = country_row["country"]
        cctld = str(country_row["cctld"]).lower()

        languages = [lang.strip().lower() for lang in str(country_row["languages"]).split(",")]

        print(f"\nProcessing {country}")

        # 1. Alle Webseiten mit passender ccTLD
        candidates = crux[crux["origin"].apply(get_cctld) == cctld].copy()

        print(f"  ccTLD candidates: {len(candidates)}")

        # 2. Top 100 nach CrUX-Rank
        candidates = candidates.sort_values("rank")

        # 3. Sprache prüfen
        valid_websites = []
        for _, row in candidates.iterrows():
            origin = row["origin"]
            rank = row["rank"]

            language = normalize_language(detect_language(origin))

            if language in languages:
                valid_websites.append({
                    "continent": continent,
                    "country": country,
                    "website": origin,
                    "rank": rank
                })

            if len(valid_websites) >= TOP_N:
                break

        print(f"  valid language matches: {len(valid_websites)}")

        continent_results.extend(valid_websites)
        results.extend(valid_websites)
    # Nach jedem Kontinent speichern
    save_continent_csv(continent, continent_results)

output = pd.DataFrame(results)

output = output[[
    "continent",
    "country",
    "website"
]]

output.to_csv(OUTPUT_FILE, index=False)

print()
print("Finished")
print(f"Rows: {len(output)}")
print(f"Saved to {OUTPUT_FILE}")