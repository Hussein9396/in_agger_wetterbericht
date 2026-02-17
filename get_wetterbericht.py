import requests
import csv
from datetime import datetime, timezone
try:
    from zoneinfo import ZoneInfo  # Python 3.9+
except ImportError:
    from backports.zoneinfo import ZoneInfo

from pathlib import Path

# --- KONFIGURATION ---
ORT = "Lohmar"
LAT = "50.816667"
LON = "7.216667"
TZ_BERLIN = ZoneInfo("Europe/Berlin")

# Aktuelle Zeit in Berlin holen
now_berlin = datetime.now(TZ_BERLIN)
now_iso = now_berlin.strftime("%Y-%m-%dT%H:%M")
API_URL = f"https://api.brightsky.dev/weather?lat={LAT}&lon={LON}&date={now_iso}&tz=Europe/Berlin"

base_path = Path(__file__).parent
csv_path = base_path / "wetterbericht.csv"

def format_wert(wert, ist_prozent=False):
    if wert is None:
        return "0"
    formatiert = str(wert).replace(".", ",")
    return f"{formatiert}%" if ist_prozent else formatiert

def hole_wetter_daten():
    print(f"Hole Wetterdaten für {ORT} (Lokalzeit Berlin)...")
    try:
        response = requests.get(API_URL, timeout=20)
        response.raise_for_status()
        data = response.json()
        all_hours = data.get("weather", [])
        
        # Vergleichszeitpunkt auf die volle Stunde gerundet (in Berlin Zeit)
        vergleich_zeit = now_berlin.replace(minute=0, second=0, microsecond=0)
        
        forecast_selection = []
        for hour_data in all_hours:
            # Zeitstempel von API (kommt als UTC+1/+2) in Berlin-Objekt umwandeln
            ts_api = datetime.fromisoformat(hour_data['timestamp']).astimezone(TZ_BERLIN)
            
            if ts_api >= vergleich_zeit:
                forecast_selection.append(hour_data)
            if len(forecast_selection) == 3:
                break
        
        existierende = set()
        if csv_path.exists():
            with csv_path.open("r", encoding="utf-8") as f:
                reader = csv.DictReader(f, delimiter=";")
                for row in reader:
                    existierende.add(f"{row['Datum']}-{row['Zeit']}")

        neue_zeilen = []
        # Zeitstempel der Abfrage auch in Berlin-Zeit
        abfrage_zeit = now_berlin.strftime("%d.%m.%Y %H:%M:%S")

        for item in forecast_selection:
            ts_local = datetime.fromisoformat(item['timestamp']).astimezone(TZ_BERLIN)
            datum_str = ts_local.strftime("%d.%m.%Y")
            zeit_str = ts_local.strftime("%H:00")
            
            if f"{datum_str}-{zeit_str}" not in existierende:
                neue_zeilen.append({
                    "Ort": ORT,
                    "Datum": datum_str,
                    "Zeit": zeit_str,
                    "Temperatur": format_wert(item.get('temperature')),
                    "Feuchtigkeit_Prozent": format_wert(item.get('relative_humidity')),
                    "Wind_kmh": format_wert(item.get('wind_speed')),
                    "Bedingung": item.get('condition', 'Unbekannt').capitalize(),
                    "Wolken_Prozent": format_wert(item.get('cloud_cover')),
                    "Regen_Wahrscheinlichkeit": f"{item.get('precipitation_probability', 0)}%",
                    "Regen_Menge_mm": format_wert(item.get('precipitation')),
                    "Abfrage_Zeitpunkt": abfrage_zeit
                })
        
        return neue_zeilen
    except Exception as e:
        print(f"Fehler: {e}")
        return []

def speichere_in_csv(zeilen):
    if not zeilen:
        print("Keine neuen Daten.")
        return
    fieldnames = ["Ort", "Datum", "Zeit", "Temperatur", "Feuchtigkeit_Prozent", "Wind_kmh", "Bedingung", "Wolken_Prozent", "Regen_Wahrscheinlichkeit", "Regen_Menge_mm", "Abfrage_Zeitpunkt"]
    file_exists = csv_path.exists()
    with csv_path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=";")
        if not file_exists:
            writer.writeheader()
        writer.writerows(zeilen)
    print(f"{len(zeilen)} Einträge gespeichert.")

if __name__ == "__main__":
    daten = hole_wetter_daten()
    speichere_in_csv(daten)