"""
compute_aqi.py

Computes the official CPCB Air Quality Index (AQI) from delhi_master_dataset_v2.csv,
following the CPCB National Air Quality Index methodology (2014 notification):

  1. Each pollutant's raw hourly readings are first turned into a ROLLING
     AVERAGE over the correct averaging window -- CPCB's breakpoint table
     is defined for 24-hour averages (PM10, PM2.5, NO2, SO2) or 8-hour
     averages (CO, O3), NOT instantaneous hourly readings. Using raw
     hourly values against these breakpoints would be a methodologically
     incorrect application of the table.
  2. Each pollutant's rolling-average concentration is converted into a
     "sub-index" (0-500 scale) via CPCB's piecewise-linear breakpoint
     table -- a straight-line interpolation between the two nearest
     published breakpoints.
  3. The overall AQI for a row is the MAXIMUM of all available sub-indices
     (the official CPCB "worst pollutant wins" rule) -- never an average.
  4. Per CPCB's own rule, an AQI is only reported when at least 3 of the
     pollutant sub-indices are available AND at least one of them is a
     particulate (PM10 or PM2.5). Rows that don't meet this are left as
     AQI = NaN rather than silently computed from too little data.

Breakpoint table source: CPCB (2014) National Air Quality Index, as
published in the official CPCB report and cross-verified against a
peer-reviewed reproduction (Table 1, CPCB 2014 breakpoints).
Units expected: PM10/PM2.5/NO2/SO2/O3 in ug/m3, CO in mg/m3 -- exactly
what delhi_master_dataset_v2.csv already contains after add_pollutants.py's
unit conversion step.

Output: delhi_master_dataset_v3.csv -- same as v2, plus:
  - aqi                     : the computed AQI (NaN if too few pollutants)
  - dominant_pollutant      : which pollutant's sub-index was the maximum
  - n_pollutants_available  : how many sub-indices went into this row's AQI
  - <pollutant>_subindex    : each pollutant's individual sub-index (for
                              inspection/debugging, not just the final AQI)
"""

import numpy as np
import pandas as pd

INPUT_FILE = "delhi_Master_dataset_v2.csv"
OUTPUT_FILE = "delhi_Master_dataset_v3.csv"

# Averaging window CPCB uses for each pollutant's breakpoint table.
AVERAGING_HOURS = {
    "pm25": 24,
    "pm10": 24,
    "no2": 24,
    "so2": 24,
    "co": 8,
    "o3": 8,
}

# CPCB (2014) breakpoint table: (concentration_lo, concentration_hi, index_lo, index_hi)
# Units: ug/m3 for pm25/pm10/no2/so2/o3, mg/m3 for co.
# The last tier's concentration_hi is used only as the slope anchor for
# extrapolating beyond the "Severe" tier (Delhi regularly exceeds it) --
# it is NOT a hard cap, since CPCB's own table is open-ended above 500.
BREAKPOINTS = {
    "pm25": [(0, 30, 0, 50), (30, 60, 51, 100), (60, 90, 101, 200),
             (90, 120, 201, 300), (120, 250, 301, 400), (250, 380, 401, 500)],
    "pm10": [(0, 50, 0, 50), (50, 100, 51, 100), (100, 250, 101, 200),
             (250, 350, 201, 300), (350, 430, 301, 400), (430, 550, 401, 500)],
    "no2":  [(0, 40, 0, 50), (40, 80, 51, 100), (80, 180, 101, 200),
             (180, 280, 201, 300), (280, 400, 301, 400), (400, 520, 401, 500)],
    "so2":  [(0, 40, 0, 50), (40, 80, 51, 100), (80, 380, 101, 200),
             (380, 800, 201, 300), (800, 1600, 301, 400), (1600, 2000, 401, 500)],
    "o3":   [(0, 50, 0, 50), (50, 100, 51, 100), (100, 168, 101, 200),
             (168, 208, 201, 300), (208, 748, 301, 400), (748, 900, 401, 500)],
    "co":   [(0, 1.0, 0, 50), (1.0, 2.0, 51, 100), (2.0, 10, 101, 200),
             (10, 17, 201, 300), (17, 34, 301, 400), (34, 45, 401, 500)],
}

# AQI is only valid with at least this many pollutants, and at least one
# of them must be a particulate -- per CPCB's own minimum-data rule.
MIN_POLLUTANTS_FOR_AQI = 3
PARTICULATE_POLLUTANTS = {"pm25", "pm10"}


def sub_index(conc, breakpoints):
    """Piecewise-linear interpolation of a concentration into a 0-500+ sub-index."""
    if pd.isna(conc) or conc < 0:
        return np.nan

    for i, (bp_lo, bp_hi, i_lo, i_hi) in enumerate(breakpoints):
        is_last_tier = (i == len(breakpoints) - 1)
        if bp_lo <= conc <= bp_hi or (is_last_tier and conc > bp_hi):
            return i_lo + (i_hi - i_lo) / (bp_hi - bp_lo) * (conc - bp_lo)
    return np.nan  # conc below the first tier's lo (shouldn't happen after the conc<0 check)


def add_rolling_averages(df):
    """
    Add a '<pollutant>_avg' column per pollutant, using CPCB's correct
    averaging window, computed PER STATION so one station's data never
    bleeds into another's rolling window.
    """
    df = df.sort_values(["location", "datetime"]).reset_index(drop=True)

    for pollutant, hours in AVERAGING_HOURS.items():
        if pollutant not in df.columns:
            continue
        # Require at least 75% of the window's hours present, same
        # completeness bar used elsewhere in this pipeline, so a rolling
        # average isn't computed from just 1-2 real readings.
        min_periods = max(1, int(hours * 0.75))
        df[f"{pollutant}_avg"] = (
            df.groupby("location")[pollutant]
              .transform(lambda s: s.rolling(hours, min_periods=min_periods).mean())
        )
    return df


def compute_row_aqi(row):
    subindices = {}
    for pollutant in AVERAGING_HOURS:
        avg_col = f"{pollutant}_avg"
        if avg_col not in row or pd.isna(row[avg_col]):
            continue
        subindices[pollutant] = sub_index(row[avg_col], BREAKPOINTS[pollutant])

    n_available = len(subindices)
    has_particulate = any(p in subindices for p in PARTICULATE_POLLUTANTS)

    if n_available < MIN_POLLUTANTS_FOR_AQI or not has_particulate:
        return pd.Series({"aqi": np.nan, "dominant_pollutant": None, "n_pollutants_available": n_available})

    dominant = max(subindices, key=subindices.get)
    return pd.Series({
        "aqi": subindices[dominant],
        "dominant_pollutant": dominant,
        "n_pollutants_available": n_available,
    })


def main():
    df = pd.read_csv(INPUT_FILE, parse_dates=["datetime"])
    print(f"Loaded {len(df)} rows, {df['location'].nunique()} stations")

    df = add_rolling_averages(df)

    for pollutant in AVERAGING_HOURS:
        avg_col = f"{pollutant}_avg"
        if avg_col in df.columns:
            n_valid = df[avg_col].notna().sum()
            print(f"  {pollutant}: {n_valid}/{len(df)} rows have a valid "
                  f"{AVERAGING_HOURS[pollutant]}h rolling average")

    print("\nComputing per-pollutant sub-indices and overall AQI...")
    for pollutant in AVERAGING_HOURS:
        avg_col = f"{pollutant}_avg"
        if avg_col in df.columns:
            df[f"{pollutant}_subindex"] = df[avg_col].apply(lambda v: sub_index(v, BREAKPOINTS[pollutant]))

    aqi_results = df.apply(compute_row_aqi, axis=1)
    df["aqi"] = aqi_results["aqi"]
    df["dominant_pollutant"] = aqi_results["dominant_pollutant"]
    df["n_pollutants_available"] = aqi_results["n_pollutants_available"]

    n_valid_aqi = df["aqi"].notna().sum()
    print(f"\nAQI computed for {n_valid_aqi}/{len(df)} rows "
          f"({n_valid_aqi/len(df)*100:.1f}%) -- the rest didn't have "
          f"{MIN_POLLUTANTS_FOR_AQI}+ pollutants including a particulate.")

    if n_valid_aqi > 0:
        print("\nDominant pollutant breakdown (among rows with a valid AQI):")
        print(df["dominant_pollutant"].value_counts().to_string())
        print(f"\nAQI distribution:\n{df['aqi'].describe().to_string()}")

    df.to_csv(OUTPUT_FILE, index=False)
    print(f"\nSaved {OUTPUT_FILE} ({len(df)} rows, {len(df.columns)} columns)")


if __name__ == "__main__":
    main()