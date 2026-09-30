import os
import time
import requests
import pandas as pd
from datetime import datetime, timedelta
 
API_KEY = os.environ.get("OPENAQ_API_KEY")
BASE_URL = "https://api.openaq.org/v3"
HEADERS = {"X-API-Key": API_KEY}
 
# Delhi's rough center coordinates. We search within a radius (meters) to
# catch NCR stations too (Gurugram, Noida, Ghaziabad, Faridabad).
DELHI_LAT, DELHI_LON = 28.6139, 77.2090
SEARCH_RADIUS_M = 25000  # 40 km, covers most of NCR
 
# How far back to pull data. Start smaller (30 days) to test the pipeline
# before requesting years of history.
DAYS_BACK = 30
 
PM25_PARAMETER_ID = 2  # OpenAQ's fixed ID for PM2.5
 
 
def get_delhi_pm25_locations():
    """Find monitoring locations near Delhi that report PM2.5."""
    url = f"{BASE_URL}/locations"
    params = {
        "coordinates": f"{DELHI_LAT},{DELHI_LON}",
        "radius": SEARCH_RADIUS_M,
        "parameters_id": PM25_PARAMETER_ID,
        "limit": 100,
    }
    resp = requests.get(url, headers=HEADERS, params=params)
    resp.raise_for_status()
    return resp.json()["results"]
 
 
def get_pm25_sensor_id(location):
    """Each location has a list of sensors (one per pollutant). Find PM2.5's."""
    for sensor in location.get("sensors", []):
        if sensor.get("parameter", {}).get("id") == PM25_PARAMETER_ID:
            return sensor["id"]
    return None
 
 
def get_sensor_measurements(sensor_id, date_from, date_to):
    """Pull hourly PM2.5 measurements for one sensor, handling pagination."""
    url = f"{BASE_URL}/sensors/{sensor_id}/measurements/hourly"
    all_records = []
    page = 1
    while True:
        params = {
            "datetime_from": date_from,
            "datetime_to": date_to,
            "limit": 1000,
            "page": page,
        }
        resp = requests.get(url, headers=HEADERS, params=params)
        if resp.status_code != 200:
            print(f"  Warning: sensor {sensor_id} page {page} returned {resp.status_code}")
            break
        data = resp.json()
        results = data.get("results", [])
        all_records.extend(results)
        if len(results) < 1000:
            break
        page += 1
        time.sleep(0.3)  # be polite to the rate limit
    return all_records
 
 
def main():
    if not API_KEY:
        raise SystemExit(
            "No API key found. Set OPENAQ_API_KEY as an environment variable first."
        )
 
    date_to = datetime.utcnow()
    date_from = date_to - timedelta(days=DAYS_BACK)
    date_from_str = date_from.strftime("%Y-%m-%dT%H:%M:%SZ")
    date_to_str = date_to.strftime("%Y-%m-%dT%H:%M:%SZ")
 
    print("Finding Delhi NCR PM2.5 stations...")
    locations = get_delhi_pm25_locations()
    print(f"Found {len(locations)} locations.")
 
    all_rows = []
    for loc in locations:
        sensor_id = get_pm25_sensor_id(loc)
        if sensor_id is None:
            continue
 
        loc_name = loc.get("name", "unknown")
        lat = loc.get("coordinates", {}).get("latitude")
        lon = loc.get("coordinates", {}).get("longitude")
 
        print(f"Fetching PM2.5 history for: {loc_name} (sensor {sensor_id})")
        measurements = get_sensor_measurements(sensor_id, date_from_str, date_to_str)
 
        for m in measurements:
            all_rows.append({
                "datetime": m.get("period", {}).get("datetimeFrom", {}).get("utc"),
                "location": loc_name,
                "latitude": lat,
                "longitude": lon,
                "pm25": m.get("value"),
            })
 
    if not all_rows:
        print("No measurements retrieved. Check your API key, radius, or date range.")
        return
 
    df = pd.DataFrame(all_rows)
    df["datetime"] = pd.to_datetime(df["datetime"])
    df = df.sort_values(["location", "datetime"]).reset_index(drop=True)
 
    out_path = "delhiPm25.csv"
    df.to_csv(out_path, index=False)
 
    print("\nDone.")
    print(f"Saved {len(df)} rows across {df['location'].nunique()} stations to {out_path}")
    print("\nPreview:")
    print(df.head())
    print("\nRows per station:")
    print(df["location"].value_counts())
 
 
if __name__ == "__main__":
    main()