"""
fetch_weather_openmeteo.py

Fetches historical hourly weather data from Open-Meteo for each of your
PM2.5 stations, over the SAME date range as your existing PM2.5 data.
No API key needed.

WHY PER-STATION, NOT ONE CITY-WIDE PULL:
Delhi NCR spans a wide area - wind and temperature at Gurugram can differ
meaningfully from Ghaziabad on a given hour. Fetching weather at each
station's exact coordinates keeps the weather-PM2.5 relationship physically
accurate rather than smeared across the whole region.

Input:  delhi_pm25_features.csv   (to get station list, coordinates, and date range)
Output: delhi_weather.csv         (one row per station per hour)

USAGE:
    python fetch_weather_openmeteo.py
"""

import time
import requests
import pandas as pd

INPUT_FILE = "delhiPm25_features.csv"
OUTPUT_FILE = "delhi_Weather.csv"

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

# The weather variables that matter for your inversion/ventilation/dispersion
# features later. Keep this list here (not scattered across scripts) so it's
# easy for teammates to see exactly what's available.
HOURLY_VARS = [
    "temperature_2m",
    "relative_humidity_2m",
    "wind_speed_10m",
    "wind_direction_10m",
    "surface_pressure",
    "precipitation",
]


def get_station_list(df):
    """One row per unique station with its coordinates."""
    stations = (
        df[["location", "latitude", "longitude"]]
        .drop_duplicates(subset="location")
        .reset_index(drop=True)
    )
    return stations


def fetch_weather_for_station(lat, lon, start_date, end_date):
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": ",".join(HOURLY_VARS),
        "timezone": "Asia/Kolkata",  # matches the IST timestamps already in your PM2.5 data
    }
    resp = requests.get(ARCHIVE_URL, params=params)
    resp.raise_for_status()
    return resp.json()


def main():
    print(f"Loading {INPUT_FILE} to get station list and date range...")
    pm25_df = pd.read_csv(INPUT_FILE, parse_dates=["datetime"])

    stations = get_station_list(pm25_df)
    print(f"Found {len(stations)} unique stations.")

    # Use the same date range as your PM2.5 data. Open-Meteo wants plain
    # dates (YYYY-MM-DD), not full timestamps.
    start_date = pm25_df["datetime"].min().strftime("%Y-%m-%d")
    end_date = pm25_df["datetime"].max().strftime("%Y-%m-%d")
    print(f"Fetching weather for {start_date} to {end_date}...")

    all_frames = []
    for _, row in stations.iterrows():
        station, lat, lon = row["location"], row["latitude"], row["longitude"]
        print(f"  Fetching weather for: {station}")

        data = fetch_weather_for_station(lat, lon, start_date, end_date)
        hourly = data.get("hourly", {})

        station_df = pd.DataFrame(hourly)
        station_df["location"] = station
        all_frames.append(station_df)

        time.sleep(0.2)  # be polite, avoid hammering the free API

    weather_df = pd.concat(all_frames, ignore_index=True)
    weather_df = weather_df.rename(columns={"time": "datetime"})
    weather_df["datetime"] = pd.to_datetime(weather_df["datetime"])
    # Localize to Asia/Kolkata so this matches the tz-aware IST timestamps
    # already in delhi_pm25_features.csv (the API returned local time values,
    # but pandas parsed them as timezone-naive).
    weather_df["datetime"] = weather_df["datetime"].dt.tz_localize("Asia/Kolkata")

    weather_df.to_csv(OUTPUT_FILE, index=False)

    print(f"\nDone. Saved {len(weather_df)} rows to {OUTPUT_FILE}")
    print("\nColumns:", weather_df.columns.tolist())
    print("\nSample:")
    print(weather_df.head())
    print("\nMissing values per column:")
    print(weather_df.isna().sum())


if __name__ == "__main__":
    main()