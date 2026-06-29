import pandas as pd
import requests
import warnings
import tldextract
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
from langdetect import detect
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

COUNTRIES_FILE = "../countries/country_selection.csv"
CRUX_FILE = "../crux/202605.csv"

LANGUAGE_CACHE_FILE = "../websites/website_languages.csv"
OUTPUT_FILE = "../websites/language_percentage_by_country.csv"

MAX_WORKERS = 30
TIMEOUT = 6


def get_cctld(origin):
    ext = tldextract.extract(origin)
    return "." + ext.suffix.lower() if ext.suffix else ""


def normalize_language(lang):
    if not isinstance(lang, str) or not lang.strip():
        return None
    return lang.lower().split("-")[0].strip()


def detect_language(origin):
    try:
        response = requests.get(
            origin,
            timeout=TIMEOUT,
            headers={"User-Agent": "Mozilla/5.0"}
        )

        soup = BeautifulSoup(response.text, "html.parser")

        html_tag = soup.find("html")
        if html_tag and html_tag.get("lang"):
            return normalize_language(html_tag.get("lang"))

        text = soup.get_text(" ", strip=True)
        text = text[:5000]

        if len(text) < 100:
            return None

        return normalize_language(detect(text))

    except Exception:
        return None


def load_language_cache():
    path = Path(LANGUAGE_CACHE_FILE)

    if path.exists():
        return pd.read_csv(path)

    return pd.DataFrame(columns=["origin", "detected_language"])


def save_language_cache(cache_df):
    Path(LANGUAGE_CACHE_FILE).parent.mkdir(parents=True, exist_ok=True)
    cache_df.to_csv(LANGUAGE_CACHE_FILE, index=False)


def update_language_cache(origins):
    cache_df = load_language_cache()

    already_checked = set(cache_df["origin"].dropna())
    missing_origins = [origin for origin in origins if origin not in already_checked]

    print(f"Bereits im Cache: {len(already_checked)}")
    print(f"Neu zu prüfen: {len(missing_origins)}")

    new_results = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(detect_language, origin): origin
            for origin in missing_origins
        }

        for i, future in enumerate(as_completed(futures), start=1):
            origin = futures[future]
            language = future.result()

            new_results.append({
                "origin": origin,
                "detected_language": language
            })

            if i % 500 == 0:
                print(f"{i}/{len(missing_origins)} neue Webseiten geprüft...")

                temp_df = pd.concat(
                    [cache_df, pd.DataFrame(new_results)],
                    ignore_index=True
                ).drop_duplicates(subset=["origin"], keep="last")

                save_language_cache(temp_df)

    if new_results:
        cache_df = pd.concat(
            [cache_df, pd.DataFrame(new_results)],
            ignore_index=True
        ).drop_duplicates(subset=["origin"], keep="last")

        save_language_cache(cache_df)

    return cache_df


def main():
    countries = pd.read_csv(COUNTRIES_FILE)
    crux = pd.read_csv(CRUX_FILE)

    countries["cctld"] = countries["cctld"].str.lower().str.strip()
    countries["languages"] = countries["languages"].apply(normalize_language)

    crux["ccTLD"] = crux["origin"].apply(get_cctld)

    relevant_cctlds = set(countries["cctld"])
    relevant_origins = crux.loc[
        crux["ccTLD"].isin(relevant_cctlds),
        "origin"
    ].drop_duplicates().tolist()

    print(f"Relevante Webseiten insgesamt: {len(relevant_origins)}")

    language_cache = update_language_cache(relevant_origins)

    crux_with_lang = crux.merge(language_cache, on="origin", how="left")

    results = []

    for _, row in countries.iterrows():
        continent = row["continent"]
        country = row["country"]
        cctld = row["cctld"]
        expected_language = row["languages"]

        subset = crux_with_lang[crux_with_lang["ccTLD"] == cctld]

        total_websites = len(subset)
        detected_websites = subset["detected_language"].notna().sum()
        language_matches = (
            subset["detected_language"] == expected_language
        ).sum()
        failed = total_websites - detected_websites

        percent_of_all = (
            language_matches / total_websites * 100
            if total_websites > 0 else 0
        )

        percent_of_detected = (
            language_matches / detected_websites * 100
            if detected_websites > 0 else 0
        )

        results.append({
            "continent": continent,
            "country": country,
            "cctld": cctld,
            "expected_language": expected_language,
            "total_websites": total_websites,
            "detected_websites": detected_websites,
            "failed_websites": failed,
            "language_matches": language_matches,
            "percent_of_all": round(percent_of_all, 2),
            "percent_of_detected": round(percent_of_detected, 2)
        })

        print(
            f"{country}: {language_matches}/{total_websites} "
            f"({round(percent_of_all, 2)}%)"
        )

    output_df = pd.DataFrame(results)

    Path(OUTPUT_FILE).parent.mkdir(parents=True, exist_ok=True)
    output_df.to_csv(OUTPUT_FILE, index=False)

    print(f"Fertig: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()