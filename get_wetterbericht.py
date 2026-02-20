import requests
import csv
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from pathlib import Path

# --- KONFIGURATION ---
ORT = "Lohmar"
LAT = "50.816667"
LON = "7.216667"
TZ_BERLIN = ZoneInfo("Europe/Berlin")

base_path = Path(__file__).parent
csv_path = base_path / "wetterbericht.csv"

FIELDNAMES = [
    "Ort", "Datum", "Zeit",
    "Temperatur", "Feuchtigkeit_Prozent", "Wind_kmh",
    "Bedingung", "Wolken_Prozent",
    "Regen_Wahrscheinlichkeit", "Regen_Menge_mm",
    "Abfrage_Zeitpunkt"
]

def floor_to_hour(dt: datetime) -> datetime:
    return dt.replace(minute=0, second=0, microsecond=0)

def format_wert(wert):
    # keep your comma formatting; keep empty as "0"
    if wert is None:
        return "0"
    return str(wert).replace(".", ",")

def read_existing_hours():
    """
    Returns:
      existing_keys: set of "dd.mm.yyyy-HH:00" already present
      last_saved_hour: latest saved datetime (Berlin) or None
    """
    existing_keys = set()
    last_saved_hour = None

    if not csv_path.exists():
        return existing_keys, None

    with csv_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            key = f"{row['Datum']}-{row['Zeit']}"
            existing_keys.add(key)

            # parse to datetime to find latest
            dt = datetime.strptime(row["Datum"] + " " + row["Zeit"], "%d.%m.%Y %H:00")
            dt = dt.replace(tzinfo=TZ_BERLIN)
            if last_saved_hour is None or dt > last_saved_hour:
                last_saved_hour = dt

    return existing_keys, last_saved_hour

def build_target_hours(now_hour: datetime, last_saved_hour: datetime | None):
    """
    Option A:
    - always want now_hour, now+1, now+2
    - if last_saved_hour is behind now_hour, backfill missing hours (last+1 .. now)
    """
    targets = {now_hour + timedelta(hours=i) for i in range(3)}

    if last_saved_hour is not None and last_saved_hour < now_hour:
        h = last_saved_hour + timedelta(hours=1)
        while h <= now_hour:
            targets.add(h)
            h += timedelta(hours=1)

    return sorted(targets)

def fetch_brightsky(start_hour: datetime):
    # ask from a bit earlier to be robust; BrightSky returns a block anyway
    start = (start_hour - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M")
    url = (
        f"https://api.brightsky.dev/weather"
        f"?lat={LAT}&lon={LON}&date={start}&tz=Europe/Berlin"
    )
    r = requests.get(url, timeout=20)
    r.raise_for_status()
    return r.json().get("weather", [])

def hole_wetter_daten():
    now_berlin = datetime.now(TZ_BERLIN)
    now_hour = floor_to_hour(now_berlin)

    existing_keys, last_saved_hour = read_existing_hours()
    targets = build_target_hours(now_hour, last_saved_hour)

    # only write rows not already present
    missing_targets = []
    for h in targets:
        key = f"{h.strftime('%d.%m.%Y')}-{h.strftime('%H:00')}"
        if key not in existing_keys:
            missing_targets.append(h)

    if not missing_targets:
        print("Keine neuen Daten (alle Zielstunden bereits vorhanden).")
        return []

    all_hours = fetch_brightsky(min(missing_targets))

    # Map API data by Berlin hour (floored)
    api_by_hour = {}
    for item in all_hours:
        ts = datetime.fromisoformat(item["timestamp"]).astimezone(TZ_BERLIN)
        api_by_hour[floor_to_hour(ts)] = item

    abfrage_zeit = now_berlin.strftime("%d.%m.%Y %H:%M:%S")
    neue_zeilen = []

    for h in missing_targets:
        item = api_by_hour.get(h)
        if not item:
            print(f"Warnung: Keine API-Daten für {h.isoformat()} gefunden, überspringe.")
            continue

        neue_zeilen.append({
            "Ort": ORT,
            "Datum": h.strftime("%d.%m.%Y"),
            "Zeit": h.strftime("%H:00"),
            "Temperatur": format_wert(item.get("temperature")),
            "Feuchtigkeit_Prozent": format_wert(item.get("relative_humidity")),
            "Wind_kmh": format_wert(item.get("wind_speed")),
            "Bedingung": item.get("condition", "Unbekannt").capitalize(),
            "Wolken_Prozent": format_wert(item.get("cloud_cover")),
            "Regen_Wahrscheinlichkeit": f"{item.get('precipitation_probability', 0)}%",
            "Regen_Menge_mm": format_wert(item.get("precipitation")),
            "Abfrage_Zeitpunkt": abfrage_zeit
        })

    print("Zielstunden:", [h.strftime("%d.%m.%Y %H:00") for h in targets])
    print("Neu zu schreiben:", [h.strftime("%d.%m.%Y %H:00") for h in missing_targets])

    return neue_zeilen

def speichere_in_csv(zeilen):
    if not zeilen:
        return

    file_exists = csv_path.exists()
    with csv_path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES, delimiter=";")
        if not file_exists:
            writer.writeheader()
        writer.writerows(zeilen)

    print(f"{len(zeilen)} Einträge gespeichert.")

if __name__ == "__main__":
    daten = hole_wetter_daten()
    speichere_in_csv(daten)