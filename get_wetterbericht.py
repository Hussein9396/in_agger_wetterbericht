import csv
from datetime import datetime, timedelta
from pathlib import Path
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

# --- CONFIGURATION ---
URL = "https://kachelmannwetter.com/de/wetter/2876218-lohmar"
base_path = Path(__file__).parent
csv_path = base_path / "wetterbericht.csv"

def get_weather_data():
    with sync_playwright() as p:
        # Launch browser (headless=True is required for GitHub Actions)
        browser = p.chromium.launch(headless=True)
        # Use a realistic viewport and user agent
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        print(f"Opening {URL}...")
        page.goto(URL, wait_until="networkidle")

        # Wait specifically for the nexthours container to ensure AJAX loaded
        page.wait_for_selector(".nexthours-hour", timeout=15000)
        
        # Get the rendered HTML
        html = page.content()
        browser.close()
        return html

def parse_and_save(html):
    soup = BeautifulSoup(html, 'html.parser')
    forecast_items = soup.find_all("div", class_="nexthours-hour")[:3]
    
    if not forecast_items:
        print("No forecast items found in HTML.")
        return

    rows_to_log = []
    german_time_now = datetime.now() + timedelta(hours=1)

    for item in forecast_items:
        try:
            time_str = item.find("div", class_="fc-hours").get_text(strip=True).replace(" Uhr", "")
            temp = item.find("div", class_="fc-temp").get_text(strip=True)
            # Find title in the symbol div
            symbol_div = item.find("div", class_="fc-symbol")
            condition = symbol_div.get("title", "N/A") if symbol_div else "N/A"
            
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
            print(f"Error parsing block: {e}")

    if rows_to_log:
        fieldnames = ["Datum", "Vorhersage_Zeit", "Temperatur", "Bedingung", "Regen_Chance", "Zeit_der_Abfrage"]
        file_exists = csv_path.exists()
        with csv_path.open("a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=";")
            if not file_exists:
                writer.writeheader()
            writer.writerows(rows_to_log)
        print(f"Successfully logged {len(rows_to_log)} rows to {csv_path.name}")

# --- EXECUTION ---
try:
    rendered_html = get_weather_data()
    parse_and_save(rendered_html)
except Exception as e:
    print(f"Script failed: {e}")