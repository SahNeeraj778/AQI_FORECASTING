"""
add_pollutants.py

Takes the five newly-fetched pollutant files (delhi_pm10.csv, delhi_no2.csv,
delhi_so2.csv, delhi_co.csv, delhi_o3.csv) and:
  1. Converts each from UTC to IST, matching how delhi_pm25.csv/
     delhi_master_dataset.csv were already handled.
  2. Runs the SAME station-quality rule used for PM2.5: keep a station only
     if it has >=85% completeness AND >=500 expected hours -- computed
     SEPARATELY per pollutant, since a station can be reliable for PM2.5
     but sparse for, say, SO2.
  3. Interpolates gaps of <=6 hours only (same rule as PM2.5); longer gaps
     are left as NaN on purpose, not filled.
  4. Merges each pollutant onto delhi_master_dataset.csv by station+hour,
     reporting % unmatched per pollutant so you can see coverage loss.

Outputs:
  - delhi_master_dataset_v2.csv  (master dataset + up to 5 new pollutant columns)
  - pollutant_station_quality_report.csv  (per-pollutant, per-station stats)

Run this AFTER delhi_master_dataset.csv and the five delhi_<pollutant>.csv
files already exist in the same folder.
"""

import pandas as pd
import numpy as np

POLLUTANT_FILES = {
    "pm10": "delhi_pm10.csv",
    "no2": "delhi_no2.csv",
    "so2": "delhi_so2.csv",
    "co": "delhi_co.csv",
    "o3": "delhi_o3.csv",
}

MASTER_FILE = "delhi_Master_dataset.csv"
OUTPUT_FILE = "delhi_Master_dataset_v2.csv"
QUALITY_REPORT_FILE = "Pollutant_station_quality_report.csv"

MIN_COMPLETENESS = 0.85
MIN_EXPECTED_HOURS = 500
MAX_INTERPOLATION_GAP_HOURS = 6

# Standard ppb -> ug/m3 conversion: ug/m3 = ppb * molecular_weight / 24.45
# (24.45 = molar volume of an ideal gas in L/mol at 25 C, 1 atm -- the
# standard reference condition used for this conversion).
MOLAR_MASS_G_PER_MOL = {"so2": 64.07, "no2": 46.01, "o3": 48.00}


def convert_to_cpcb_units(pollutant, value, units):
    """
    Convert a raw fetched value into the unit CPCB's breakpoint table
    expects for this pollutant: ug/m3 for pm10/no2/so2/o3, mg/m3 for co.

    Real-run findings baked in here (2026-09 fetch):
      - pm10, o3: came back as ug/m3 already -- no conversion needed.
      - so2, no2: came back as ppb (physically plausible values) ->
        converted with the standard ppb-to-ug/m3 formula.
      - co: labeled 'ppb' by OpenAQ but the actual values (median ~0.9,
        max ~6) are far too small to be real ppb -- ambient CO in ppb is
        normally in the hundreds to thousands. They line up almost
        exactly with CPCB's own mg/m3 breakpoints instead, so this is
        treated as an OpenAQ unit-label error and passed through
        UNCONVERTED as mg/m3. This is a judgment call based on a
        plausibility check, not a documented guarantee -- if you can,
        spot-check one CO reading against a live CPCB/SAFAR dashboard
        value for the same station and hour to confirm.
    """
    units_l = str(units).lower()

    if pollutant == "co":
        if "g/m" in units_l and "µ" in units_l:  # ug/m3 -> mg/m3
            return value / 1000.0
        # 'ppb' (mislabeled) or already 'mg/m3': pass through unconverted.
        return value

    if "g/m" in units_l:
        return value  # already ug/m3 for pm10/no2/so2/o3

    if pollutant in MOLAR_MASS_G_PER_MOL:
        mw = MOLAR_MASS_G_PER_MOL[pollutant]
        if "ppb" in units_l:
            return value * mw / 24.45
        if "ppm" in units_l:
            return value * mw / 24.45 * 1000
        print(f"    WARNING: unrecognized units '{units}' for {pollutant}, using raw value unconverted")

    return value


def utc_to_ist(series_utc_str):
    """Convert a column of UTC ISO timestamp strings to naive IST timestamps."""
    dt_utc = pd.to_datetime(series_utc_str, utc=True)
    dt_ist = dt_utc.dt.tz_convert("Asia/Kolkata").dt.tz_localize(None)
    return dt_ist


def longest_gap_hours(hourly_series):
    """
    Given a boolean Series indexed by a complete hourly DatetimeIndex
    (True = value present), return the longest run of consecutive missing
    hours. Used the same way as the PM2.5 pipeline's gap check.
    """
    is_missing = ~hourly_series
    if not is_missing.any():
        return 0
    # Identify consecutive missing runs by grouping on changes in is_missing
    group_id = (is_missing != is_missing.shift()).cumsum()
    run_lengths = is_missing.groupby(group_id).sum()
    missing_run_lengths = run_lengths[is_missing.groupby(group_id).first()]
    return int(missing_run_lengths.max()) if len(missing_run_lengths) else 0


def process_pollutant(pollutant, filepath, quality_rows):
    print(f"\n=== {pollutant.upper()} ===")
    df = pd.read_csv(filepath)
    df["datetime"] = utc_to_ist(df["datetime_utc"])
    df = df.dropna(subset=["datetime"])

    if "units" in df.columns:
        seen_units = df["units"].unique().tolist()
        df["value"] = df.apply(lambda r: convert_to_cpcb_units(pollutant, r["value"], r["units"]), axis=1)
        target_unit = "mg/m3" if pollutant == "co" else "ug/m3"
        print(f"  Raw units seen: {seen_units} -> converted to {target_unit}")
    else:
        print("  WARNING: no 'units' column in this file -- assuming values are already "
              "in CPCB-compatible units, but this has NOT been verified")

    df = df[["datetime", "location", "value"]]

    full_range = pd.date_range(df["datetime"].min(), df["datetime"].max(), freq="h")
    expected_hours = len(full_range)

    kept_frames = []
    for station, station_df in df.groupby("location"):
        station_df = station_df.drop_duplicates(subset="datetime").set_index("datetime")
        hourly = station_df["value"].reindex(full_range)

        present_mask = hourly.notna()
        completeness = present_mask.mean()
        gap = longest_gap_hours(present_mask)

        kept = (completeness >= MIN_COMPLETENESS) and (expected_hours >= MIN_EXPECTED_HOURS)

        quality_rows.append({
            "pollutant": pollutant,
            "station": station,
            "expected_hours": expected_hours,
            "observed_hours": int(present_mask.sum()),
            "completeness_pct": round(completeness * 100, 1),
            "longest_gap_hours": gap,
            "kept": kept,
        })

        if kept:
            # Interpolate only short gaps (<=6h); longer gaps stay NaN.
            hourly_interp = hourly.interpolate(method="linear", limit=MAX_INTERPOLATION_GAP_HOURS)
            station_out = hourly_interp.reset_index()
            station_out.columns = ["datetime", pollutant]
            station_out["location"] = station
            kept_frames.append(station_out)

    n_kept = sum(1 for r in quality_rows if r["pollutant"] == pollutant and r["kept"])
    n_total = sum(1 for r in quality_rows if r["pollutant"] == pollutant)
    print(f"  Stations kept: {n_kept}/{n_total} (>= {int(MIN_COMPLETENESS*100)}% completeness)")

    if not kept_frames:
        print(f"  WARNING: no stations passed the quality threshold for {pollutant}")
        return None

    return pd.concat(kept_frames, ignore_index=True)


def main():
    master = pd.read_csv(MASTER_FILE, parse_dates=["datetime"])

    # Your master dataset's 'datetime' column may be timezone-AWARE
    # (e.g. dtype datetime64[us, UTC+05:30]) while the pollutant timestamps
    # below are converted to timezone-NAIVE IST. Pandas refuses to merge
    # a tz-aware column against a tz-naive one, so we normalize the master
    # column to naive here -- the underlying wall-clock IST time is
    # unchanged, only the tz label is dropped.
    if master["datetime"].dt.tz is not None:
        master["datetime"] = master["datetime"].dt.tz_localize(None)

    print(f"Loaded master dataset: {len(master)} rows, {master['location'].nunique()} stations")

    quality_rows = []
    for pollutant, filepath in POLLUTANT_FILES.items():
        pollutant_df = process_pollutant(pollutant, filepath, quality_rows)
        if pollutant_df is None:
            continue

        before = len(master)
        master = master.merge(pollutant_df, on=["datetime", "location"], how="left")
        unmatched_pct = master[pollutant].isna().mean() * 100
        print(f"  Merged onto master: {unmatched_pct:.1f}% of master rows have no {pollutant} value "
              f"(expected -- only {master['location'].isin(pollutant_df['location'].unique()).sum()} "
              f"of {before} master rows are from a kept {pollutant} station)")

    quality_df = pd.DataFrame(quality_rows)
    quality_df.to_csv(QUALITY_REPORT_FILE, index=False)
    print(f"\nSaved station quality report: {QUALITY_REPORT_FILE}")

    master.to_csv(OUTPUT_FILE, index=False)
    print(f"Saved updated master dataset: {OUTPUT_FILE} ({len(master)} rows, {len(master.columns)} columns)")


if __name__ == "__main__":
    main()