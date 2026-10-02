# Global Website Comparison

Dieses Repository enthält die Implementierung und die Auswertungsdaten der Bachelorarbeit

**„Vergleich von Webseiten verschiedener Länder anhand struktureller, visueller und technischer Metriken“**

an der Universität Kassel, Fachbereich Elektrotechnik/Informatik.

Ziel der Arbeit ist die automatisierte Untersuchung von Webseiten verschiedener Länder. Dafür werden HTML-Dokumente, Netzwerkdaten und Full-Page-Screenshots ausgewertet. Die daraus berechneten strukturellen, technischen und visuellen Metriken werden anschließend auf Länder- und Kontinentebene verglichen.

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
| `websites/` | zusammengestellte Webseitenlisten; `top100_websites.csv` bildet die zentrale Ausgangsdatei der Analyse |
| `scripts/html/` | Berechnung, Prüfung und Visualisierung der strukturellen HTML-Metriken |
| `scripts/har/` | Berechnung, Prüfung und Visualisierung der technischen Netzwerkmetriken |
| `scripts/visually/` | Berechnung, Prüfung und Visualisierung der Screenshot-Metriken |
| `csv/` | berechnete Metriken der untersuchten Webseiten |
| `charts/` | aus den Metrikdateien erzeugte Diagramme |
| `references/` | zusätzliche Referenzdaten für die Auswertung und Einordnung |

## Datenfluss

Der grundlegende Ablauf der Analyse ist:

```text
websites/top100_websites.csv
            │
            ├───────────────┬──────────────────┐
            │               │                  │
            ▼               ▼                  ▼
      HTML / DOM        HAR-Daten         Screenshots
      MinIO +           ClickHouse        MinIO +
      ClickHouse                          ClickHouse
            │               │                  │
            ▼               ▼                  ▼
 html_metrics.csv   har_metrics.csv   visually_metrics.csv
            │               │                  │
            ▼               ▼                  ▼
   Qualitätsprüfung  Qualitätsprüfung  Qualitätsprüfung
            │               │                  │
            ▼               ▼                  ▼
     charts/html       charts/har       charts/visually
```

Die Datei

```text
websites/top100_websites.csv
```

enthält die untersuchten Webseiten zusammen mit ihrer Zuordnung zu Land und Kontinent und dient als gemeinsame Grundlage der drei Analysebereiche.

---

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

Für jede Webseite wird zunächst über ClickHouse die passende Crawl-ID bestimmt. Anschließend wird im MinIO-Bucket `crawler-dom` die zu dieser Crawl-ID gehörende Version des HTML-Dokuments gesucht.

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

### Funktionen

#### `normalize_url(url)`

Extrahiert aus einer URL den Domainnamen.

Beispiel:

```text
https://www.example.com/ → www.example.com
```

Der normalisierte Domainname wird für die Bildung der MinIO-Objektpfade verwendet.

#### `find_crawl_id(url)`

Sucht in der ClickHouse-Tabelle `crawls` nach dem neuesten gültigen Crawl einer Webseite.

Berücksichtigt werden Crawls mit dem festgelegten Bachelorarbeits-Tag und einem vorhandenen DOM.

Die Funktion gibt die gefundene `crawl_id` zurück.

#### `find_all_crawl_ids(url)`

Lädt alle verfügbaren Crawl-IDs einer Webseite mit einem der konfigurierten BA- oder CrUX-Tags.

Diese Funktion wird für die Nachsuche verwendet, wenn für den zuerst ausgewählten Crawl kein passendes HTML-Dokument gefunden wurde.

#### `build_versioned_object_names(url)`

Erzeugt die möglichen MinIO-Objektpfade einer Webseite.

Dabei werden sowohl HTTPS als auch HTTP berücksichtigt:

```text
https/<domain>.html
http/<domain>.html
```

#### `get_metadata_value(metadata, searched_key)`

Sucht einen bestimmten Wert innerhalb der MinIO-Metadaten.

Die Funktion wird insbesondere verwendet, um die im Objekt gespeicherte Crawl-ID über

```text
x-amz-meta-crawl-id
```

auszulesen.

#### `read_html_from_minio(object_name, version_id=None)`

Lädt eine bestimmte Version eines HTML-Dokuments aus MinIO.

Zurückgegeben werden:

```text
HTML-Inhalt
Dateigröße
```

#### `find_html(url, crawl_id)`

Sucht für eine Webseite nach einem HTML-Dokument, dessen gespeicherte Crawl-ID mit der gesuchten Crawl-ID übereinstimmt.

#### `find_matching_version(object_name, crawl_id)`

Durchsucht die Versionen eines MinIO-Objekts.

Da MinIO-Versionierung verwendet wird, können unter demselben Objektpfad HTML-Dokumente verschiedener Crawls liegen. Die Funktion liest deshalb die Metadaten der einzelnen Versionen und wählt die Version mit der passenden Crawl-ID aus.

#### `count_text_blocks(soup)`

Bestimmt die Anzahl größerer Textblöcke im HTML-Dokument.

Berücksichtigt werden unter anderem:

```text
p
div
section
article
main
aside
header
footer
li
td
th
blockquote
```

Ein Element wird als Textblock gezählt, wenn sein bereinigter Text mindestens 30 Zeichen enthält.

#### `calculate_metrics(html, html_size)`

Berechnet die eigentlichen strukturellen Metriken aus dem HTML-Dokument.

Hier werden unter anderem Links, Bilder, Formulare, Tabellen, Buttons sowie Zeichen, Wörter und Textblöcke gezählt.

#### `save_result(result)`

Speichert ein neu berechnetes Ergebnis in `html_metrics.csv`.

Die Datei wird schrittweise erweitert, sodass bereits berechnete Ergebnisse erhalten bleiben.

#### `update_result(result)`

Aktualisiert einen bereits vorhandenen Eintrag.

Dies wird insbesondere bei der Nachsuche verwendet, wenn für eine zunächst nicht gefundene Webseite später ein geeigneter Crawl gefunden wird.

---

### `scripts/html/check_html_metrics.py`

Dieses Skript überprüft die erzeugte Datei

```text
csv/html_metrics.csv
```

auf Vollständigkeit und Plausibilität.

Unter anderem werden geprüft:

- Anzahl der erwarteten Webseiten
- doppelte Webseiten
- fehlende Webseiten
- unerwartete Webseiten
- fehlende Crawl-IDs
- fehlende Metrikwerte
- ungültige `found`-Werte
- negative Metrikwerte

#### `is_missing(series)`

Erkennt fehlende Werte wie:

```text
NaN
None
null
""
```

#### `convert_found(series)`

Konvertiert unterschiedliche Darstellungen eines booleschen Wertes in `True` beziehungsweise `False`.

Beispielsweise:

```text
true
1
yes
false
0
no
```

---

### `scripts/html/html_to_chart.py`

Erstellt aus

```text
csv/html_metrics.csv
```

Diagramme für die strukturellen Metriken.

Die Ergebnisse werden unter

```text
charts/html/
```

gespeichert.

Für jede numerische Metrik werden Boxplots nach

- Land und
- Kontinent

erzeugt.

Die Diagramme zeigen unter anderem Median, Mittelwert und Interquartilsabstand.

Das Skript besitzt keine separaten Analysefunktionen, sondern führt die Erstellung der Diagramme direkt beim Start aus.

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

Die HAR-Einträge werden direkt aus der ClickHouse-Tabelle `har_entries` geladen.

Für jede Webseite werden folgende Metriken berechnet:

- `num_requests` – Gesamtzahl der Netzwerkrequests
- `transferred_bytes` – gesamte übertragene Datenmenge
- `html` – Anzahl geladener HTML-Ressourcen
- `css` – Anzahl geladener CSS-Ressourcen
- `javascript` – Anzahl geladener JavaScript-Ressourcen
- `images` – Anzahl geladener Bildressourcen
- `fonts` – Anzahl geladener Schriftarten

### Funktionen

#### `find_crawl_id(url)`

Bestimmt den neuesten Crawl der angegebenen Webseite mit dem benötigten Crawl-Tag.

#### `find_all_crawl_ids(url)`

Lädt alle geeigneten BA- und CrUX-Crawls einer Webseite.

Die Funktion wird verwendet, wenn der zunächst ausgewählte Crawl keine HAR-Einträge enthält.

#### `analyze_har(crawl_id)`

Lädt die HAR-Einträge des Crawls aus ClickHouse.

Verwendet werden unter anderem:

```text
entry_id
request_url
response_content_type
response_content_size
```

Negative Größenwerte werden vor der Auswertung auf `0` gesetzt.

Anhand des Content-Types werden die Ressourcen anschließend den Kategorien HTML, CSS, JavaScript, Bilder und Schriftarten zugeordnet.

Die Funktion gibt die berechneten HAR-Metriken als Dictionary zurück.

#### `save_result(result)`

Fügt ein Analyseergebnis zu `har_metrics.csv` hinzu.

#### `update_result(result)`

Aktualisiert einen bereits vorhandenen Datensatz, wenn während der Nachsuche ein geeigneter Crawl gefunden wurde.

---

### `scripts/har/check_har_metrics.py`

Überprüft

```text
csv/har_metrics.csv
```

auf Vollständigkeit und Plausibilität.

Zusätzlich zu allgemeinen Prüfungen werden HAR-spezifische Bedingungen kontrolliert.

Dazu gehören beispielsweise:

- numerische Metrikwerte
- keine negativen Werte
- mindestens ein Request bei erfolgreichen Crawls
- keine übertragene Datenmenge ohne Requests
- Summe der erfassten Ressourcentypen darf nicht größer als die Gesamtzahl der Requests sein

#### `is_missing(series)`

Prüft eine Pandas-Spalte auf fehlende Werte.

#### `convert_found(series)`

Normalisiert die unterschiedlichen Darstellungen des `found`-Status.

---

### `scripts/har/har_to_chart.py`

Liest

```text
csv/har_metrics.csv
```

und erstellt Boxplots der technischen Metriken.

Ausgabe:

```text
charts/har/
```

Für jede numerische Metrik wird jeweils ein Vergleich nach Land und nach Kontinent erzeugt.

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

Die Screenshots werden aus dem MinIO-Bucket

```text
crawler-screenshots
```

geladen.

Berechnet werden:

- fünf dominante Farben
- Anteil jeder dominanten Farbe
- Anzahl unterschiedlicher Farben
- Farbenentropie
- durchschnittliche Sättigung
- durchschnittliche Helligkeit
- Weißraumanteil
- Screenshot-Höhe
- Screenshot-Dateigröße

### Funktionen

#### `normalize_url(url)`

Extrahiert die Domain aus einer URL.

#### `find_crawl_id(url)`

Bestimmt über ClickHouse den neuesten Crawl mit vorhandenem Full-Page-Screenshot.

#### `find_all_crawl_ids(url)`

Ermittelt alle verfügbaren BA- und CrUX-Crawls mit vorhandenem Screenshot.

#### `build_versioned_object_names(url)`

Erzeugt die möglichen Screenshot-Pfade:

```text
https/<domain>.full.png
http/<domain>.full.png
```

#### `get_metadata_value(metadata, searched_key)`

Liest einen bestimmten Wert aus den MinIO-Metadaten.

#### `read_screenshot_from_minio(object_name, version_id=None)`

Lädt einen Screenshot aus MinIO und gibt

```text
PIL-Bild
Dateigröße
```

zurück.

#### `find_screenshot(url, crawl_id)`

Sucht nach dem Full-Page-Screenshot, der zum gewünschten Crawl gehört.

#### `find_matching_version(object_name, crawl_id)`

Durchsucht die gespeicherten MinIO-Versionen und vergleicht deren Metadaten mit der gewünschten Crawl-ID.

#### `calculate_metrics(image, file_size)`

Berechnet die visuellen Eigenschaften eines Screenshots.

Zunächst werden die RGB-Pixel des Screenshots analysiert.

Die Anzahl unterschiedlicher RGB-Werte ergibt `unique_colors`. Aus deren Häufigkeitsverteilung wird anschließend die Farbenentropie berechnet.

Der Screenshot wird außerdem in den HSV-Farbraum umgewandelt. Daraus werden die durchschnittliche Sättigung und Helligkeit bestimmt.

Ein Pixel gilt für die Berechnung des Weißraumanteils als weiß beziehungsweise nahezu weiß, wenn

```text
brightness > 245
saturation < 15
```

gilt.

Für die Bestimmung der dominanten Farben wird eine reproduzierbare Stichprobe von maximal 10.000 Pixeln verwendet. Diese Pixel werden mit K-Means in fünf Farbcluster aufgeteilt. Die Clusterzentren bilden die fünf dominanten Farben.

#### `save_result(result)`

Speichert neue Ergebnisse in `visually_metrics.csv`.

#### `update_result(result)`

Aktualisiert vorhandene Ergebnisse nach einer erfolgreichen Nachsuche.

---

### `scripts/visually/check_visually_metrics.py`

Überprüft

```text
csv/visually_metrics.csv
```

auf Vollständigkeit und gültige Werte.

Neben den allgemeinen Prüfungen werden beispielsweise kontrolliert:

- RGB-Werte müssen aus drei Werten zwischen 0 und 255 bestehen
- `whitespace_ratio` muss zwischen 0 und 1 liegen
- Sättigung muss zwischen 0 und 255 liegen
- Helligkeit muss zwischen 0 und 255 liegen
- Screenshot-Höhe muss größer als 0 sein
- Screenshot-Dateigröße muss größer als 0 sein
- `unique_colors` muss mindestens 1 sein
- Farbenentropie darf nicht negativ sein

#### `is_missing(series)`

Erkennt fehlende Werte.

#### `convert_found(series)`

Konvertiert den `found`-Status in boolesche Werte.

#### `valid_rgb(value)`

Prüft, ob eine dominante Farbe als gültiges RGB-Tupel gespeichert ist.

Beispiel:

```text
(125, 200, 42)
```

Alle drei Werte müssen zwischen `0` und `255` liegen.

---

### `scripts/visually/visually_to_chart.py`

Erzeugt die Diagramme für die visuellen Metriken.

Eingabe:

```text
csv/visually_metrics.csv
```

Ausgabe:

```text
charts/visually/
```

Neben Boxplots nach Ländern und Kontinenten werden repräsentative Farbpaletten sowie Scatterplots zwischen ausgewählten visuellen Metriken erzeugt.

### Funktionen

#### `parse_rgb(value)`

Konvertiert die in der CSV gespeicherten RGB-Werte wieder in Python-Tupel.

Beispiel:

```text
"(125, 200, 42)"
```

wird zu:

```python
(125, 200, 42)
```

#### `calculate_representative_palette(...)`

Berechnet eine repräsentative Farbpalette für eine Gruppe von Webseiten.

Eine Gruppe kann beispielsweise

- ein Land oder
- ein Kontinent

sein.

Die fünf dominanten Farben aller zugehörigen Webseiten werden gemeinsam betrachtet und anhand ihrer jeweiligen Farbanteile gewichtet.

Anschließend werden mittels K-Means bis zu fünf repräsentative Farbcluster bestimmt.

#### `create_palette_chart(...)`

Erzeugt aus den zuvor berechneten repräsentativen Farben ein Farbdiagramm.

Für jede Gruppe werden die fünf Farben zusammen mit ihrem prozentualen Anteil dargestellt.

Zusätzlich erstellt das Skript Scatterplots ausgewählter Metrikpaare und berechnet dafür die Spearman-Korrelation.

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

Die Standardwerte der Analyse sind auf die für die Bachelorarbeit verwendete Web-Kraken-Infrastruktur der Universität Kassel abgestimmt.

---

# Benötigte Python-Bibliotheken

Die Analyse verwendet unter anderem:

```text
pandas
clickhouse-connect
minio
beautifulsoup4
numpy
Pillow
opencv-python
scikit-learn
scipy
matplotlib
seaborn
```

Die Pakete können beispielsweise mit `pip` installiert werden:

```bash
pip install pandas clickhouse-connect minio beautifulsoup4 numpy Pillow opencv-python scikit-learn scipy matplotlib seaborn
```

---

# Ausführen der Analyse

Die Skripte verwenden relative Dateipfade. Sie sollten deshalb aus ihrem jeweiligen Unterverzeichnis ausgeführt werden.

## HTML-Metriken

```bash
cd scripts/html

python html_metrics_from_minio.py
python check_html_metrics.py
python html_to_chart.py
```

## HAR-Metriken

```bash
cd scripts/har

python har_metrics_from_clickhouse.py
python check_har_metrics.py
python har_to_chart.py
```

## Visuelle Metriken

```bash
cd scripts/visually

python visually_metrics_from_minio.py
python check_visually_metrics.py
python visually_to_chart.py
```

Damit ergibt sich für jeden Analysebereich grundsätzlich derselbe Ablauf:

```text
Metriken berechnen
        ↓
Ergebnisse prüfen
        ↓
Diagramme erzeugen
```

## Ergebnisdateien

Nach der Berechnung befinden sich die zentralen Datensätze unter:

```text
csv/html_metrics.csv
csv/har_metrics.csv
csv/visually_metrics.csv
```

Die daraus erzeugten Abbildungen befinden sich unter:

```text
charts/html/
charts/har/
charts/visually/
```

## Lizenz

Dieses Projekt steht unter der MIT License. Weitere Informationen befinden sich in der Datei `LICENSE`.