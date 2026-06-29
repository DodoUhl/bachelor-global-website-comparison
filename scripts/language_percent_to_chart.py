import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

INPUT_FILE = "../websites/language_percentage_by_country.csv"
OUTPUT_FILE = "../charts/language_percentage_chart.png"

# Welche Prozent-Spalte soll geplottet werden?
# Empfehlung: percent_of_detected
PERCENT_COLUMN = "percent_of_detected"


def main():
    df = pd.read_csv(INPUT_FILE)
    df = df.dropna(subset=[PERCENT_COLUMN])
    df = df[df[PERCENT_COLUMN] > 0] 
    df = df.sort_values(PERCENT_COLUMN, ascending=True)
    df["label"] = (df["country"] + " (" + df["detected_websites"].astype(int).astype(str) + ")")

    plt.figure(figsize=(10, 10))

    plt.barh(df["label"], df[PERCENT_COLUMN])

    plt.xlabel("Webseiten mit passender Sprache (%)")
    plt.ylabel("Land")
    plt.title("Anteil der Webseiten mit passender Landessprache nach ccTLD")

    plt.xlim(0, 100)

    for index, value in enumerate(df[PERCENT_COLUMN]):
        plt.text(
            value + 1,
            index,
            f"{value:.1f}%",
            va="center"
        )

    plt.tight_layout()

    Path(OUTPUT_FILE).parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(OUTPUT_FILE, dpi=300)
    plt.show()

    print(f"Chart gespeichert unter: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()