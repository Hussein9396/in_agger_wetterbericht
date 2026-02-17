import requests
import csv
from datetime import datetime, timezone
from pathlib import Path

# --- Configuration ---
ORT = "Lohmar"
LAT = "50.816667"
LON = "7.216667"
now_dt = datetime.now()
now_iso = now_dt.strftime("%Y-%m-%dT%H:%M")
API_URL = f"https://api.brightsky.dev/weather?lat={LAT}&lon={LON}&date={now_iso}&tz=Europe/Berlin"

base_path = Path(__file__).parent
csv_path = base_path / "wetterbericht.csv"

def get_current_weather():
    print(f"Hole aktuelle Wetterdaten für {ORT}...")
    try:
        response = requests.get(API_URL, timeout=20)
        response.raise_for_status()
        data = response.json()
        
        all_hours = data.get("weather", [])
        now_utc = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
        
        current_data = None
        for hour in all_hours:
            ts = datetime.fromisoformat(hour['timestamp'])
            if ts == now_utc:
                current_data = hour
                break
        
        if not current_data:
            return None

        # Get current weather data and format it
        row = {
            "Ort": ORT,
            "Datum": now_dt.strftime("%d.%m.%Y"),
            "Zeit": now_dt.strftime("%H:00"),
            "Temperatur": f"{current_data.get('temperature', 0)}".replace(".", ","),
            "Feuchtigkeit_Prozent": current_data.get('relative_humidity', 0),
            "Wind_kmh": f"{current_data.get('wind_speed', 0)}".replace(".", ","),
            "Bedingung": current_data.get('condition', 'Unbekannt').capitalize(),
            "Wolken_Prozent": current_data.get('cloud_cover', 0),
            "Regen_Wahrscheinlichkeit": f"{current_data.get('precipitation_probability', 0)}%",
            "Regen_Menge_mm": f"{current_data.get('precipitation', 0)}".replace(".", ","),
            "Abfrage_Zeitpunkt": now_dt.strftime("%d.%m.%Y %H:%M:%S")
        }
        return row

    except Exception as e:
        print(f"Fehler: {e}")
        return None

def speichere_in_csv(row):
    if not row:
        return

    fieldnames = [
        "Ort", "Datum", "Zeit", "Temperatur", "Feuchtigkeit_Prozent", 
        "Wind_kmh", "Bedingung", "Wolken_Prozent", 
        "Regen_Wahrscheinlichkeit", "Regen_Menge_mm", "Abfrage_Zeitpunkt"
    ]
    file_exists = csv_path.exists()

    with csv_path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=";")
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)
    
    print(f"Wetterbericht für {ORT} am {row['Datum']} um {row['Zeit']} gespeichert.")

if __name__ == "__main__":
    daten = get_current_weather()
    speichere_in_csv(daten)