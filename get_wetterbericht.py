import os
import requests
from datetime import datetime, timedelta
import csv
from pathlib import Path
from bs4 import BeautifulSoup

# --- CONFIGURATION ---
URL = "https://kachelmannwetter.com/de/ajax_pub/weathernexthoursdays?city_id=2876218&lang=de&unit_t=celsius&unit_v=kmh&unit_l=metrisch&unit_r=joule&unit_p=hpa&nf=pointcomma&tf=1"

headers = {
    "Accept": "text/html, */*; q=0.01",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36",
    "Referer": "https://kachelmannwetter.com/de/wetter/2876218-lohmar"
}

# Paths
base_path = Path(__file__).parent
csv_path = base_path / "wetterbericht.csv"

# 1. FETCH DATA
r = requests.get(URL, headers=headers, timeout=30)
r.raise_for_status()
soup = BeautifulSoup(r.text, 'html.parser')

# 2. PARSE FORECAST (First 3 hours)
# We look for the div containers representing each hour
forecast_items = soup.find_all("div", class_="nexthours-hour")[:3]

rows_to_log = []
german_time_now = datetime.now() + timedelta(hours=1) 

for item in forecast_items:
    try:
        # Extracting details based on your HTML snippet
        time_str = item.find("div", class_="fc-hours").get_text(strip=True).replace(" Uhr", "")
        temp = item.find("div", class_="fc-temp").get_text(strip=True)
        condition = item.find("div", class_="fc-symbol").get("title")
        
        # Rain probability is inside fc-rain, we just want the percentage text
        rain_div = item.find("div", class_="fc-rain")
        rain_prob = rain_div.get_text(strip=True) if rain_div else "0%"

        row = {
            "Datum": german_time_now.strftime("%d.%m.%Y"),
            "Vorhersage_Zeit": time_str,
            "Temperatur": temp,
            "Bedingung": condition,
            "Regen_Chance": rain_prob,
            "Zeit_der_Abfrage": german_time_now.strftime("%d.%m.%Y %H:%M:%S") + " (UTC+1)"
        }
        rows_to_log.append(row)
    except Exception as e:
        print(f"Error parsing an hour block: {e}")

# 3. SAVE TO CSV
fieldnames = ["Datum", "Vorhersage_Zeit", "Temperatur", "Bedingung", "Regen_Chance", "Zeit_der_Abfrage"]
file_exists = csv_path.exists()

with csv_path.open("a", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=";")
    if not file_exists:
        writer.writeheader()
    writer.writerows(rows_to_log)

print(f"Logged {len(rows_to_log)} forecast hours to {csv_path.name}")