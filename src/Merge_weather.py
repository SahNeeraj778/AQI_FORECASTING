"""
merge_weather.py

Merges delhi_weather.csv onto delhi_pm25_features.csv (station + hourly
timestamp match) and adds physically-motivated derived features:
  - temperature_change_3h: proxy for overnight cooling / inversion tendency
  - ventilation_index: wind_speed combined with the temperature-drop proxy,
    representing how well the atmosphere is likely to disperse pollutants

Input:  delhi_pm25_features.csv
        delhi_weather.csv
Output: delhi_master_dataset.csv   (ready for baseline modeling)

USAGE:
    python merge_weather.py
"""

import pandas as pd

PM25_FEATURES_FILE = "delhiPm25_features.csv"
WEATHER_FILE = "delhi_Weather.csv"
OUTPUT_FILE = "delhi_Master_dataset.csv"


def load_data():
    pm25_df = pd.read_csv(PM25_FEATURES_FILE, parse_dates=["datetime"])
    weather_df = pd.read_csv(WEATHER_FILE, parse_dates=["datetime"])
    return pm25_df, weather_df


def merge_datasets(pm25_df, weather_df):
    # Weather has its own lat/lon columns from the fetch step; drop them
    # before merging so we keep the PM2.5 side's station coordinates and
    # avoid duplicate/confusing lat/lon columns after the join.
    weather_df = weather_df.drop(columns=["latitude", "longitude"], errors="ignore")

    merged = pd.merge(
        pm25_df,
        weather_df,
        on=["location", "datetime"],
        how="left",  # keep every PM2.5 row; flag weather rows that failed to match
    )
    return merged


def add_derived_features(df):
    df = df.sort_values(["location", "datetime"])
    grouped_temp = df.groupby("location")["temperature_2m"]

    # Positive value = warming over the last 3h, negative = cooling.
    # A sharp negative value overnight is our inversion-tendency proxy -
    # we are NOT claiming this equals a measured inversion strength (no
    # vertical temperature profile data), just a physically defensible
    # surface-based proxy, as flagged in the original project scope.
    df["temperature_change_3h"] = grouped_temp.transform(lambda s: s - s.shift(3))

    # Ventilation index: higher wind + more atmospheric instability (i.e.
    # NOT cooling sharply) suggests better pollutant dispersion. This is a
    # simple, transparent combination for the MVP - not a scientific
    # constant, and should be described as such in any writeup.
    # We add a small offset so very calm, sharply-cooling hours (the worst
    # dispersion conditions) score lowest.
    df["ventilation_index"] = df["wind_speed_10m"] * (
        1 + df["temperature_change_3h"].clip(lower=-5, upper=5) / 5
    )

    return df


def report_merge_quality(merged):
    unmatched = merged["temperature_2m"].isna().sum()
    total = len(merged)
    print(f"Merge check: {unmatched} of {total} rows have no matching weather data "
          f"({unmatched / total * 100:.1f}%).")
    if unmatched > 0:
        print("Rows with unmatched weather, by station:")
        print(merged[merged["temperature_2m"].isna()]["location"].value_counts())


def main():
    print("Loading PM2.5 features and weather data...")
    pm25_df, weather_df = load_data()

    print("Merging on station + hourly timestamp...")
    merged = merge_datasets(pm25_df, weather_df)

    report_merge_quality(merged)

    print("Adding inversion-tendency and ventilation-index features...")
    merged = add_derived_features(merged)

    merged.to_csv(OUTPUT_FILE, index=False)

    print(f"\nDone. Saved master dataset to {OUTPUT_FILE}")
    print(f"Final shape: {merged.shape}")
    print("\nColumns:", merged.columns.tolist())
    print("\nSample:")
    cols_to_show = [
        "datetime", "location", "pm25", "wind_speed_10m",
        "temperature_change_3h", "ventilation_index",
    ]
    print(merged[cols_to_show].dropna().head())


if __name__ == "__main__":
    main()