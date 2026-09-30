"""
fetch_pollutants_delhi.py

Fetches hourly PM10, NO2, SO2, CO, and O3 data from OpenAQ v3 for the SAME
Delhi NCR stations you already used for PM2.5, over the same date window.

Why reuse the same stations instead of discovering new ones?
So every pollutant lines up with locations you've already vetted, rather
than introducing new station IDs with unknown data quality.

Requires: OPENAQ_API_KEY environment variable (same key as fetch_pm25_delhi.py)
Outputs: one CSV per pollutant (delhi_pm10.csv, delhi_no2.csv, delhi_so2.csv,
delhi_co.csv, delhi_o3.csv), each with columns:
  datetime_utc, value, location, latitude, longitude, parameter

Station lookup:
  delhi_pm25.csv only has 'location', 'latitude', 'longitude' -- no OpenAQ
  location ID. So for each unique station we look up its OpenAQ location ID
  by searching /v3/locations with its exact coordinates and a tight radius,
  then confirm the name matches before trusting the result.

v2 fixes (based on a real run against the live API):
  - OpenAQ's /hours endpoint takes 'datetime_from'/'datetime_to', not
    'date_from'/'date_to'. The wrong names were being silently ignored,
    so the API returned each sensor's ENTIRE history instead of just the
    30-day window -- that's why the first run kept paginating to page 10+
    and timing out.
  - Any single request failure (timeout, 500, connection reset) now gets
    retried with backoff, and only skips that ONE sensor if it still
    fails -- it no longer crashes the whole script the way an uncaught
    ConnectionError did last time.

v4 fix (critical, before this data is used for AQI):
  - OpenAQ stores some gas pollutants (CO, NO2, SO2, O3) under TWO separate
    sensor entries with different units -- e.g. CO as both 'µg/m³' and
    'ppm'. The old version picked whichever sensor happened to come last
    in the API's list, with no unit check -- meaning different stations
    could silently end up in different units in the SAME output column.
    This version explicitly prefers the mass-concentration unit (µg/m³)
    for every pollutant, since that's what the CPCB breakpoint table
    uses, and records the chosen unit in a new 'units' column so nothing
    is silently ambiguous. PM10/PM2.5 aren't affected -- particulate
    matter has no ppm variant, so their data was always safe.
"""

import os
import time
from datetime import datetime

import pandas as pd
import requests

API_KEY = os.environ.get("OPENAQ_API_KEY")
if not API_KEY:
    raise RuntimeError("Set the OPENAQ_API_KEY environment variable before running this script.")

HEADERS = {"X-API-Key": API_KEY}
BASE_URL = "https://api.openaq.org/v3"

PARAMETERS = ["pm10", "no2", "so2", "co", "o3"]

# The unit CPCB's breakpoint table expects for each pollutant's mass
# concentration. We prefer a sensor reporting in this family of unit;
# ppm/ppb variants are skipped when a mass-unit sensor is also available.
MASS_UNIT_HINT = "g/m"  # matches 'µg/m³', 'mg/m³', 'ug/m3', etc.

STATION_SOURCE_FILE = "Data/delhi_pm25.csv"
COORD_SEARCH_RADIUS_METERS = 250

PAGE_LIMIT = 1000
REQUEST_TIMEOUT_SECONDS = 30
REQUEST_PAUSE_SECONDS = 0.3
MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = 3  # doubles each retry: 3s, 6s, 12s


def request_with_retry(url, params=None):
    """
    GET a URL with retries on transient failures (timeouts, 5xx errors,
    connection drops). Raises the last error if every retry is exhausted,
    so the CALLER decides whether to skip or abort -- this function's job
    is only to absorb temporary network hiccups, not permanent failures
    like a bad API key (401) or a missing resource (404).
    """
    last_exception = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(url, headers=HEADERS, params=params, timeout=REQUEST_TIMEOUT_SECONDS)
            if resp.status_code in (408, 429, 500, 502, 503, 504):
                # Transient: server/timeout/rate-limit issue, worth retrying.
                raise requests.HTTPError(f"{resp.status_code} error", response=resp)
            resp.raise_for_status()
            return resp
        except (requests.exceptions.RequestException,) as e:
            last_exception = e
            if attempt < MAX_RETRIES:
                wait = RETRY_BACKOFF_SECONDS * (2 ** (attempt - 1))
                print(f"    attempt {attempt} failed ({e}), retrying in {wait}s...")
                time.sleep(wait)
            else:
                print(f"    attempt {attempt} failed ({e}), giving up on this request")
    raise last_exception


def get_station_list_and_window():
    """
    Load the same stations you already used for PM2.5, deduplicated by
    name+coords, AND read the exact date window from the same file --
    so this fetch always matches delhi_pm25.csv regardless of what day
    you happen to run it.
    """
    df = pd.read_csv(STATION_SOURCE_FILE, parse_dates=["datetime"])
    stations = df[["location", "latitude", "longitude"]].drop_duplicates().reset_index(drop=True)
    date_from = df["datetime"].min()
    date_to = df["datetime"].max()
    print(f"Reusing {len(stations)} stations from {STATION_SOURCE_FILE}")
    print(f"Matching PM2.5 date window: {date_from} to {date_to}")
    return stations, date_from, date_to


def find_location_id(name, lat, lon):
    """Look up a station's OpenAQ location ID by its coordinates."""
    url = f"{BASE_URL}/locations"
    params = {"coordinates": f"{lat},{lon}", "radius": COORD_SEARCH_RADIUS_METERS, "limit": 5}
    try:
        resp = request_with_retry(url, params=params)
    except requests.exceptions.RequestException:
        return None

    results = resp.json().get("results", [])
    if not results:
        return None

    for r in results:
        if r.get("name", "").strip().lower() == name.strip().lower():
            return r["id"]
    return results[0]["id"]


def get_sensors_for_location(location_id):
    """
    Return {parameter_name: {"id": sensor_id, "units": units_str}} for a
    given OpenAQ location. When a pollutant has multiple sensor entries
    (e.g. CO in both µg/m³ and ppm), the mass-concentration one is kept.
    """
    url = f"{BASE_URL}/locations/{location_id}"
    resp = request_with_retry(url)
    data = resp.json()["results"][0]

    sensor_map = {}
    for sensor in data.get("sensors", []):
        param_name = sensor["parameter"]["name"]
        units = sensor["parameter"].get("units", "")
        is_mass_unit = MASS_UNIT_HINT in units.lower()

        existing = sensor_map.get(param_name)
        if existing is None:
            sensor_map[param_name] = {"id": sensor["id"], "units": units}
        elif is_mass_unit and MASS_UNIT_HINT not in existing["units"].lower():
            # Replace a previously-stored non-mass-unit sensor (e.g. ppm)
            # with this mass-unit one now that we've found it.
            sensor_map[param_name] = {"id": sensor["id"], "units": units}

    return sensor_map


def fetch_sensor_hours(sensor_id, date_from, date_to):
    """Fetch hourly-aggregated measurements for one sensor over the given date window."""
    url = f"{BASE_URL}/sensors/{sensor_id}/hours"
    params = {
        "datetime_from": date_from.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "datetime_to": date_to.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "limit": PAGE_LIMIT,
        "page": 1,
    }

    all_rows = []
    while True:
        resp = request_with_retry(url, params=dict(params))
        results = resp.json().get("results", [])
        if not results:
            break

        for r in results:
            all_rows.append({
                "datetime_utc": r["period"]["datetimeFrom"]["utc"],
                "value": r["value"],
            })

        if len(results) < PAGE_LIMIT:
            break
        params["page"] += 1
        time.sleep(REQUEST_PAUSE_SECONDS)

    return pd.DataFrame(all_rows)


def main():
    stations, date_from, date_to = get_station_list_and_window()
    rows_by_pollutant = {param: [] for param in PARAMETERS}
    unresolved_stations = []

    for _, row in stations.iterrows():
        name, lat, lon = row["location"], row["latitude"], row["longitude"]
        print(f"\nStation: {name} ({lat}, {lon})")

        location_id = find_location_id(name, lat, lon)
        if location_id is None:
            print("  Could not resolve an OpenAQ location ID for this station, skipping")
            unresolved_stations.append(name)
            continue

        try:
            sensor_map = get_sensors_for_location(location_id)
        except requests.exceptions.RequestException as e:
            print(f"  Could not fetch sensor list, skipping station ({e})")
            continue

        for param in PARAMETERS:
            sensor_info = sensor_map.get(param)
            if sensor_info is None:
                print(f"  {param}: not measured at this station, skipping")
                continue

            sensor_id = sensor_info["id"]
            units = sensor_info["units"]
            if MASS_UNIT_HINT not in units.lower():
                print(f"  {param}: WARNING -- only a '{units}' sensor found (no mass-unit "
                      f"sensor available), using it anyway but this station's {param} values "
                      f"will need unit conversion before AQI calculation")

            print(f"  {param}: fetching sensor {sensor_id} (units: {units})...")
            try:
                df = fetch_sensor_hours(sensor_id, date_from, date_to)
            except requests.exceptions.RequestException as e:
                print(f"  {param}: fetch failed after retries, skipping ({e})")
                continue

            if df.empty:
                print(f"  {param}: no data returned")
                continue

            df["location"] = name
            df["latitude"] = lat
            df["longitude"] = lon
            df["parameter"] = param
            df["units"] = units
            rows_by_pollutant[param].append(df)
            time.sleep(REQUEST_PAUSE_SECONDS)

    for param in PARAMETERS:
        if rows_by_pollutant[param]:
            combined = pd.concat(rows_by_pollutant[param], ignore_index=True)
            out_file = f"delhi_{param}.csv"
            combined.to_csv(out_file, index=False)
            print(f"\nSaved {len(combined)} rows to {out_file}")

            unit_counts = combined.groupby("units")["location"].nunique()
            print(f"  Units used: {unit_counts.to_dict()}")
            non_mass_units = [u for u in unit_counts.index if MASS_UNIT_HINT not in u.lower()]
            if non_mass_units:
                print(f"  WARNING: {param} has station(s) reporting in non-mass units "
                      f"{non_mass_units} -- these values need conversion before AQI calculation, "
                      f"they are NOT directly comparable to the mass-unit stations in this file")
        else:
            print(f"\nNo data collected for {param} across any station")

    if unresolved_stations:
        print(f"\nCould not resolve {len(unresolved_stations)} station(s) by coordinates:")
        for s in unresolved_stations:
            print(f"  - {s}")


if __name__ == "__main__":
    main()