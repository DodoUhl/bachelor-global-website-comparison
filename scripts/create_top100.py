import pandas as pd
import requests
import tldextract
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
from langdetect import detect
import warnings

# Warnungen für BeautifulSoup unterdrücken
warnings.filterwarnings(
    "ignore",
    category=XMLParsedAsHTMLWarning
)

# Dateien
COUNTRIES_FILE = "../countries/country_selection.csv"
CRUX_FILE = "../crux/202605.csv"
OUTPUT_FILE = "../websites/top100_websites.csv"

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

# CSv-Dateien einlesen
countries = pd.read_csv(COUNTRIES_FILE, sep=None, engine="python")
crux = pd.read_csv(CRUX_FILE)

results = []

# Alle Länder durchgehen
for _, country_row in countries.iterrows():
    continent = country_row["continent"]
    country = country_row["country"]
    cctld = str(country_row["cctld"]).lower()

    languages = [lang.strip().lower() for lang in str(country_row["languages"]).split(",")]

    print(f"\nProcessing {country}")

    # 1. Alle Webseiten mit passender ccTLD
    candidates = crux[crux["origin"].apply(get_cctld) == cctld].copy()

    print(f"  ccTLD candidates: {len(candidates)}")

    # 2. Sortieren nach CrUX-Rank
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

    results.extend(valid_websites)

# Ergebnisse in DataFrame umwandeln und speichern
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