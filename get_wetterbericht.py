import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import csv
from pathlib import Path
import re

# --- CONFIGURATION ---
MAIN_URL = "https://kachelmannwetter.com/de/wetter/2876218-lohmar"
AJAX_URL = "https://kachelmannwetter.com/de/ajax_pub/weathernexthoursdays?city_id=2876218&lang=de&unit_t=celsius&unit_v=kmh&unit_l=metrisch&unit_r=joule&unit_p=hpa&nf=pointcomma&tf=1"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36",
    "Accept": "text/html, */*; q=0.01",
    "Referer": MAIN_URL,
    "X-Requested-With": "XMLHttpRequest"
}

base_path = Path(__file__).parent
csv_path = base_path / "wetterbericht.csv"

def get_forecast():
    session = requests.Session()
    session.headers.update(headers)

    # 1. Visit main page to get Cookies and CSRF Token
    print("Initial connection to establish session...")
    response = session.get(MAIN_URL, timeout=30)
    response.raise_for_status()

    # Extract CSRF token from the page source (usually in a <meta> tag or JS variable)
    # Searching for: <meta name="csrf-token" content="...">
    soup_init = BeautifulSoup(response.text, 'html.parser')
    csrf_token = None
    csrf_meta = soup_init.find('meta', {'name': 'csrf-token'})
    
    if csrf_meta:
        csrf_token = csrf_meta.get('content')
    
    if csrf_token:
        session.headers.update({"X-CSRF-Token": csrf_token})
        print("CSRF Token found and applied.")

    # 2. Fetch the actual AJAX data
    print("Fetching weather data...")
    r = session.get(AJAX_URL, timeout=30)
    r.raise_for_status()
    
    soup = BeautifulSoup(r.text, 'html.parser')
    forecast_items = soup.find_all("div", class_="nexthours-hour")[:3]

    rows_to_log = []
    german_time_now = datetime.now() + timedelta(hours=1)

    for item in forecast_items:
        try:
            time_str = item.find("div", class_="fc-hours").get_text(strip=True).replace(" Uhr", "")
            temp = item.find("div", class_="fc-temp").get_text(strip=True)
            condition = item.find("div", class_="fc-symbol").get("title", "N/A")
            
            rain_div = item.find("div", class_="fc-rain")
            rain_prob = rain_div.get_text(strip=True) if rain_div else "0%"

            rows_to_log.append({
                "Datum": german_time_now.strftime("%d.%m.%Y"),
                "Vorhersage_Zeit": time_str,
                "Temperatur": temp,
                "Bedingung": condition,
                "Regen_Chance": rain_prob,
                "Zeit_der_Abfrage": german_time_now.strftime("%d.%m.%Y %H:%M:%S") + " (UTC+1)"
            })
        except Exception as e:
            print(f"Error parsing hour block: {e}")

    return rows_to_log

# --- EXECUTION ---
try:
    data = get_forecast()
    if data:
        fieldnames = ["Datum", "Vorhersage_Zeit", "Temperatur", "Bedingung", "Regen_Chance", "Zeit_der_Abfrage"]
        file_exists = csv_path.exists()
        with csv_path.open("a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=";")
            if not file_exists:
                writer.writeheader()
            writer.writerows(data)
        print(f"Successfully logged {len(data)} rows.")
except Exception as e:
    print(f"Script failed: {e}")