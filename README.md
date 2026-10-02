# Global Website Comparison

Dieses Repository enthält die Implementierung und die Auswertungsdaten der Bachelorarbeit

**„Vergleich von Webseiten verschiedener Länder anhand struktureller, visueller und technischer Metriken“**

an der Universität Kassel.

Ziel der Arbeit ist die automatisierte Untersuchung von Webseiten verschiedener Länder. Dafür werden HTML-Dokumente, HAR-Dateien und Screenshots ausgewertet. Die daraus berechneten strukturellen, technischen und visuellen Metriken werden anschließend auf Länder- und Kontinentebene dargestellt.

## Repository-Struktur

```text
bachelor-global-website-comparison/
│
├── charts/
│   ├── html/
│   ├── har/
│   └── visually/
│
├── countries/
├── crux/
├── csv/
├── references/
│
├── scripts/
│   ├── html/
│   │   ├── html_metrics_from_minio.py
│   │   ├── check_html_metrics.py
│   │   └── html_to_chart.py
│   │
│   ├── har/
│   │   ├── har_metrics_from_clickhouse.py
│   │   ├── check_har_metrics.py
│   │   └── har_to_chart.py
│   │
│   └── visually/
│       ├── visually_metrics_from_minio.py
│       ├── check_visually_metrics.py
│       └── visually_to_chart.py
│
├── websites/
│   └── top100_websites.csv
│
├── LICENSE
└── README.md
```

### Verzeichnisse

| Verzeichnis | Inhalt |
|---|---|
| `countries/` | Dateien zur Auswahl und Zuordnung der untersuchten Länder |
| `crux/` | verwendete Daten aus dem Chrome UX Report (CrUX) |
| `websites/` | zusammengestellte Webseitenlisten welche die zentrale Ausgangsdatei der Analyse bildet |
| `scripts/html/` | Berechnung, Prüfung und Visualisierung der strukturellen HTML-Metriken |
| `scripts/har/` | Berechnung, Prüfung und Visualisierung der technischen Netzwerkmetriken |
| `scripts/visually/` | Berechnung, Prüfung und Visualisierung der Screenshot-Metriken |
| `csv/` | berechnete Metriken der untersuchten Webseiten |
| `charts/` | aus den Metrikdateien erzeugte Diagramme |
| `references/` | zusätzliche Referenzdaten für die Auswertung und Einordnung |

# Python-Skripte

## 1. Strukturelle Analyse

### `scripts/html/html_metrics_from_minio.py`

Das Skript berechnet strukturelle Eigenschaften der gespeicherten HTML-Dokumente.

Als Eingabe wird verwendet:

```text
websites/top100_websites.csv
```

Die Ergebnisse werden gespeichert in:

```text
csv/html_metrics.csv
```

Aus dem HTML-Dokument werden anschließend folgende Metriken berechnet:

- `dom_size` – Größe des gespeicherten HTML-Dokuments
- `links` – Anzahl der `<a>`-Elemente
- `images` – Anzahl der `<img>`-Elemente
- `forms` – Anzahl der `<form>`-Elemente
- `tables` – Anzahl der `<table>`-Elemente
- `buttons` – Anzahl von Buttons und entsprechenden Input-Elementen
- `text_chars` – Anzahl der Textzeichen
- `text_words` – Anzahl der Wörter
- `text_blocks` – Anzahl größerer texttragender HTML-Blöcke

---

# 2. Technische Analyse

### `scripts/har/har_metrics_from_clickhouse.py`

Das Skript analysiert die beim Crawling aufgezeichneten Netzwerkrequests.

Eingabe:

```text
websites/top100_websites.csv
```

Ausgabe:

```text
csv/har_metrics.csv
```

Für jede Webseite werden folgende Metriken berechnet:

- `num_requests` – Gesamtzahl der Netzwerkrequests
- `transferred_bytes` – gesamte übertragene Datenmenge
- `html` – Anzahl geladener HTML-Ressourcen
- `css` – Anzahl geladener CSS-Ressourcen
- `javascript` – Anzahl geladener JavaScript-Ressourcen
- `images` – Anzahl geladener Bildressourcen
- `fonts` – Anzahl geladener Schriftarten

---

# 3. Visuelle Analyse

### `scripts/visually/visually_metrics_from_minio.py`

Dieses Skript analysiert die beim Crawling erzeugten Full-Page-Screenshots.

Eingabe:

```text
websites/top100_websites.csv
```

Ausgabe:

```text
csv/visually_metrics.csv
```

Berechnet werden:

- `dominant_color_1` bis `dominant_color_5` – fünf dominante Farben des Screenshots
- `dominant_color_1_ratio` bis `dominant_color_5_ratio` – jeweiliger Anteil der dominanten Farben am Screenshot
- `unique_colors` – Anzahl unterschiedlicher RGB-Farbwerte
- `color_entropy` – Entropie der Farbverteilung
- `average_saturation` – durchschnittliche Farbsättigung
- `average_brightness` – durchschnittliche Helligkeit
- `whitespace_ratio` – Anteil weißer beziehungsweise nahezu weißer Pixel
- `screenshot_height` – Höhe des Full-Page-Screenshots in Pixeln
 -`screenshot_file_size` – Dateigröße des Screenshots in Bytes

---

# Verbindung zu ClickHouse und MinIO

Die während des Crawling-Prozesses erzeugten Daten werden nicht vollständig im Repository gespeichert.

HTML-Dokumente und Screenshots werden aus MinIO geladen, während Crawl-Informationen und HAR-Daten aus ClickHouse abgefragt werden.

Für den Zugriff müssen entsprechende Umgebungsvariablen gesetzt sein.

Verwendet werden unter anderem:

```text
CLICKHOUSE_USERNAME
CLICKHOUSE_PASSWORD

MINIO_ACCESS_KEY
MINIO_SECRET_KEY
```

Zusätzlich können folgende Werte über Umgebungsvariablen angepasst werden:

```text
CLICKHOUSE_DATABASE
CLICKHOUSE_TABLE_CRAWLS
CLICKHOUSE_TABLE_HAR
CRAWL_TAG
CRAWL_TAGS
```

Die Standardwerte der Analyse sind auf die für die Bachelorarbeit verwendeten Variablen abgestimmt.
