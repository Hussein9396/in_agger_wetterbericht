import requests
import csv
from datetime import datetime, timezone
from pathlib import Path

# --- CONFIGURATION ---
LAT = "50.816667"
LON = "7.216667"

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
        
        # Use timezone-aware 'now' to match API timestamps
        now = datetime.now(timezone.utc)
        
        forecast_selection = []
        for hour_data in all_hours:
            # Parse API timestamp (which is offset-aware)
            ts = datetime.fromisoformat(hour_data['timestamp'])
            
            # Start from the current hour (ignoring minutes/seconds)
            if ts >= now.replace(minute=0, second=0, microsecond=0):
                forecast_selection.append(hour_data)
            
            if len(forecast_selection) == 3:
                break

        # Load existing timestamps to prevent duplicates if manually triggered
        existing_entries = set()
        if csv_path.exists():
            with csv_path.open("r", encoding="utf-8") as f:
                reader = csv.DictReader(f, delimiter=";")
                for row in reader:
                    existing_entries.add(f"{row['Datum']}-{row['Vorhersage_Zeit']}")

        rows_to_log = []
        for item in forecast_selection:
            time_obj = datetime.fromisoformat(item['timestamp'])
            d_str = time_obj.strftime("%d.%m.%Y")
            t_str = time_obj.strftime("%H:%M")
            
            # Only add if this specific hour isn't already in the CSV
            if f"{d_str}-{t_str}" not in existing_entries:
                rows_to_log.append({
                    "Datum": d_str,
                    "Vorhersage_Zeit": t_str,
                    "Temperatur": f"{item['temperature']}".replace(".", ","),
                    "Bedingung": item.get('condition', 'N/A').capitalize(),
                    "Regen_Chance": f"{item.get('precipitation_probability', 0)}%",
                    "Zeit_der_Abfrage": datetime.now().strftime("%d.%m.%Y %H:%M:%S")
                })
            
        return rows_to_log

    except Exception as e:
        print(f"Error fetching data: {e}")
        return []

def save_to_csv(data):
    if not data:
        print("No new unique data to save.")
        return

    fieldnames = ["Datum", "Vorhersage_Zeit", "Temperatur", "Bedingung", "Regen_Chance", "Zeit_der_Abfrage"]
    file_exists = csv_path.exists()

    with csv_path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=";")
        if not file_exists:
            writer.writeheader()
        writer.writerows(data)
    
    print(f"Successfully logged {len(data)} new entries.")

if __name__ == "__main__":
    weather_data = get_weather()
    save_to_csv(weather_data)