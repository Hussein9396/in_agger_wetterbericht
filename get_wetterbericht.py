import requests
import csv
from datetime import datetime, timezone
from pathlib import Path

# --- CONFIGURATION ---
LAT = "50.816667"
LON = "7.216667"
# Added date parameter to avoid 422 errors and ensure we start 'now'
now_iso = datetime.now().strftime("%Y-%m-%dT%H:%M")
API_URL = f"https://api.brightsky.dev/weather?lat={LAT}&lon={LON}&date={now_iso}&tz=Europe/Berlin"

base_path = Path(__file__).parent
csv_path = base_path / "wetterbericht.csv"

def get_weather():
    print(f"Fetching weather data for Lohmar ({LAT}, {LON})...")
    try:
        response = requests.get(API_URL, timeout=20)
        response.raise_for_status()
        data = response.json()
        
        all_hours = data.get("weather", [])
        now_utc = datetime.now(timezone.utc)
        
        forecast_selection = []
        for hour_data in all_hours:
            ts = datetime.fromisoformat(hour_data['timestamp'])
            # Match current hour and next two
            if ts >= now_utc.replace(minute=0, second=0, microsecond=0):
                forecast_selection.append(hour_data)
            if len(forecast_selection) == 3:
                break

        # Check existing entries to avoid duplicates
        existing_entries = set()
        if csv_path.exists():
            with csv_path.open("r", encoding="utf-8") as f:
                reader = csv.DictReader(f, delimiter=";")
                for row in reader:
                    existing_entries.add(f"{row['Datum']}-{row['Stunde']}")

        rows_to_log = []
        for item in forecast_selection:
            time_obj = datetime.fromisoformat(item['timestamp'])
            d_str = time_obj.strftime("%d.%m.%Y")
            h_str = time_obj.strftime("%H:%M")
            
            if f"{d_str}-{h_str}" not in existing_entries:
                rows_to_log.append({
                    "Datum": d_str,
                    "Stunde": h_str,
                    "Temperatur": f"{item.get('temperature', 0)}".replace(".", ","),
                    "Bedingung": item.get('condition', 'unknown').capitalize(),
                    "Regen_Chance": f"{item.get('precipitation_probability', 0)}%",
                    "Regen_Menge": f"{item.get('precipitation', 0)}".replace(".", ","),
                    "Abfrage_Zeit": datetime.now().strftime("%d.%m.%Y %H:%M:%S")
                })
            
        return rows_to_log

    except Exception as e:
        print(f"Error: {e}")
        return []

def save_to_csv(data):
    if not data:
        print("No new data.")
        return

    fieldnames = ["Datum", "Stunde", "Temperatur", "Bedingung", "Regen_Chance", "Regen_Menge", "Abfrage_Zeit"]
    file_exists = csv_path.exists()

    with csv_path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=";")
        if not file_exists:
            writer.writeheader()
        writer.writerows(data)
    print(f"Logged {len(data)} entries.")

if __name__ == "__main__":
    weather_data = get_weather()
    save_to_csv(weather_data)