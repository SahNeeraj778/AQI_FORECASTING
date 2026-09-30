"""
clean_and_engineer.py

Steps 1-3 of the PM2.5-only MVP pipeline:
  1. Clean the raw OpenAQ CSV (UTC -> IST, station quality filtering, gap interpolation)
  2. Add time-based cyclical features (hour of day, day of week)
  3. Add lag + rolling PM2.5 features

Input:  delhi_pm25.csv          (raw file from fetch_pm25_delhi.py)
Output: delhi_pm25_features.csv (clean, feature-engineered, ready for modeling)
        station_quality_report.csv (transparency: which stations kept/dropped and why)

USAGE:
    python clean_and_engineer.py
"""

import pandas as pd
import numpy as np

INPUT_FILE = "delhiPm25.csv"
OUTPUT_FILE = "delhiPm25_features.csv"
REPORT_FILE = "station_quality_report.csv"

# --- Station quality thresholds ---
# A station is "kept" only if it has enough total history AND is complete
# enough within that history. This avoids the trap of a station looking
# "100% complete" just because it only recently started reporting.
MIN_COMPLETENESS_PCT = 85
MIN_EXPECTED_HOURS = 500  # roughly 20+ days of coverage

# Gaps up to this many consecutive hours get linearly interpolated.
# Longer gaps (e.g. the ~32h regional outage) are left as NaN on purpose -
# faking hours across a known real outage would quietly corrupt lag/rolling
# features later.
MAX_GAP_HOURS_TO_FILL = 6


def load_and_convert_timezone(path):
    df = pd.read_csv(path, parse_dates=["datetime"])
    # OpenAQ timestamps are UTC. Delhi is UTC+5:30 - this matters for any
    # feature based on local time of day (rush hour, early-morning inversion).
    df["datetime"] = df["datetime"].dt.tz_convert("Asia/Kolkata")
    return df


def assess_station_quality(df):
    """For each station: completeness %, longest gap, and total expected hours."""
    rows = []
    for station, sub in df.groupby("location"):
        sub = sub.sort_values("datetime")
        full_range = pd.date_range(sub["datetime"].min(), sub["datetime"].max(), freq="h")
        missing = sorted(full_range.difference(sub["datetime"]))

        max_run, run = 0, 1
        for i in range(1, len(missing)):
            if (missing[i] - missing[i - 1]).total_seconds() == 3600:
                run += 1
                max_run = max(max_run, run)
            else:
                run = 1
        if missing:
            max_run = max(max_run, 1)

        completeness = len(sub) / len(full_range) * 100
        rows.append({
            "station": station,
            "expected_hours": len(full_range),
            "actual_rows": len(sub),
            "completeness_pct": round(completeness, 1),
            "max_gap_hours": max_run,
        })
    return pd.DataFrame(rows).sort_values("completeness_pct", ascending=False)


def filter_to_reliable_stations(quality_df):
    keep_mask = (
        (quality_df["completeness_pct"] >= MIN_COMPLETENESS_PCT)
        & (quality_df["expected_hours"] >= MIN_EXPECTED_HOURS)
    )
    kept = quality_df[keep_mask]["station"].tolist()
    dropped = quality_df[~keep_mask]["station"].tolist()
    return kept, dropped


def interpolate_short_gaps(df, kept_stations):
    """Reindex each station to a full hourly timeline and fill small gaps only."""
    filled_frames = []
    for station in kept_stations:
        sub = df[df["location"] == station].sort_values("datetime").copy()
        sub = sub.set_index("datetime")

        full_range = pd.date_range(sub.index.min(), sub.index.max(), freq="h")
        sub = sub.reindex(full_range)
        sub["location"] = station
        sub["latitude"] = sub["latitude"].ffill().bfill()
        sub["longitude"] = sub["longitude"].ffill().bfill()

        # Only fill gaps up to MAX_GAP_HOURS_TO_FILL; longer gaps stay NaN.
        sub["pm25"] = sub["pm25"].interpolate(
            method="linear", limit=MAX_GAP_HOURS_TO_FILL, limit_area="inside"
        )

        sub = sub.reset_index().rename(columns={"index": "datetime"})
        filled_frames.append(sub)

    return pd.concat(filled_frames, ignore_index=True)


def add_time_features(df):
    df["hour"] = df["datetime"].dt.hour
    df["dow"] = df["datetime"].dt.dayofweek

    # Cyclical encoding so hour 23 and hour 0 are recognized as adjacent,
    # not maximally far apart, by the model.
    df["hour_sin"] = np.sin(2 * np.pi * df["hour"] / 24)
    df["hour_cos"] = np.cos(2 * np.pi * df["hour"] / 24)
    df["dow_sin"] = np.sin(2 * np.pi * df["dow"] / 7)
    df["dow_cos"] = np.cos(2 * np.pi * df["dow"] / 7)
    return df


def add_lag_and_rolling_features(df):
    df = df.sort_values(["location", "datetime"])
    lag_hours = [1, 3, 6, 12, 24]
    rolling_windows = [3, 6, 24]

    grouped = df.groupby("location")["pm25"]

    for lag in lag_hours:
        df[f"pm25_lag_{lag}h"] = grouped.shift(lag)

    for window in rolling_windows:
        df[f"pm25_rolling_mean_{window}h"] = grouped.transform(
            lambda s: s.shift(1).rolling(window, min_periods=max(1, window // 2)).mean()
        )

    df["pm25_rolling_std_6h"] = grouped.transform(
        lambda s: s.shift(1).rolling(6, min_periods=3).std()
    )

    return df


def main():
    print("Loading raw data and converting UTC -> IST...")
    df = load_and_convert_timezone(INPUT_FILE)

    print("Assessing station quality...")
    quality_df = assess_station_quality(df)
    quality_df.to_csv(REPORT_FILE, index=False)

    kept, dropped = filter_to_reliable_stations(quality_df)
    print(f"\nKeeping {len(kept)} stations, dropping {len(dropped)}.")
    print("Dropped:", dropped)

    print("\nInterpolating short gaps (<= {}h) per station...".format(MAX_GAP_HOURS_TO_FILL))
    df_clean = interpolate_short_gaps(df, kept)

    print("Adding time-based cyclical features...")
    df_clean = add_time_features(df_clean)

    print("Adding lag + rolling PM2.5 features...")
    df_clean = add_lag_and_rolling_features(df_clean)

    df_clean.to_csv(OUTPUT_FILE, index=False)

    print(f"\nDone. Saved feature dataset to {OUTPUT_FILE}")
    print(f"Station quality report saved to {REPORT_FILE}")
    print(f"\nFinal shape: {df_clean.shape}")
    print("\nColumns:", df_clean.columns.tolist())
    print("\nSample (New Delhi, most recent rows):")
    sample = df_clean[df_clean["location"] == kept[0]].tail(5)
    print(sample[["datetime", "pm25", "pm25_lag_1h", "pm25_rolling_mean_6h", "hour_sin"]])


if __name__ == "__main__":
    main()