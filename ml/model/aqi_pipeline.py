"""
aqi_pipeline.py  -  Delhi NCR AQI Early Warning System
=======================================================
One shared pipeline used by BOTH the training notebook and the dashboard backend, so
features are built identically at training time and at prediction time.

What it adds on top of model_v4_improved.ipynb
  1. Full hourly grid per station (no silently missing hours -> shift/lag are true hours)
  2. Common forecast start time (anchor) for ALL stations, even ones that stopped early
  3. Gap handling:
       - model input : past-only (no future leakage), short carry-forward + neighbour-based estimate
       - dashboard   : linear interpolation of short gaps; PM2.5 and AQI always filled
                       (with flags so the UI can style filled points differently)
  4. Bundle (pickle) = models + everything needed to rebuild features + metrics
  5. Snapshot (JSON) = 7-day history + forecast + alerts. This is what React reads.
"""
import json
import pickle

import numpy as np
import pandas as pd

# ----------------------------------------------------------------------------- config
POLLUTANTS = ["pm25", "pm10", "no2", "so2", "co", "o3"]
OTHER_POLL = POLLUTANTS[1:]
WEATHER_COLS = [
    "temperature_2m", "relative_humidity_2m", "wind_speed_10m", "wind_direction_10m",
    "surface_pressure", "precipitation", "temperature_change_3h", "ventilation_index",
]
FILL_COLS = POLLUTANTS + ["aqi"] + WEATHER_COLS

# Must match section 6 of the notebook exactly.
FEATURE_COLS = [
    "latitude", "longitude", "pm25",
    "pm25_lag_1h", "pm25_lag_3h", "pm25_lag_6h", "pm25_lag_12h", "pm25_lag_24h",
    "pm25_rolling_mean_3h", "pm25_rolling_mean_6h", "pm25_rolling_mean_24h", "pm25_rolling_std_6h",
    "hour_sin", "hour_cos", "dow_sin", "dow_cos",
    "temperature_2m", "relative_humidity_2m", "wind_speed_10m",
    "wind_direction_sin", "wind_direction_cos",
    "surface_pressure", "precipitation", "temperature_change_3h", "ventilation_index",
    "spatial_pm25_neighbors", "spatial_aqi_neighbors",
]

# CHECK these against your dataset (Open-Meteo defaults: km/h, hPa, mm).
UNITS = {
    "pm25": "µg/m³", "pm10": "µg/m³", "no2": "µg/m³", "so2": "µg/m³", "co": "mg/m³", "o3": "µg/m³",
    "aqi": "", "temperature_2m": "°C", "relative_humidity_2m": "%", "wind_speed_10m": "km/h",
    "wind_direction_10m": "°", "surface_pressure": "hPa", "precipitation": "mm",
    "temperature_change_3h": "°C", "ventilation_index": "",
}

CFG = dict(
    # --- model input (past-only, must stay leakage-safe) ---
    model_ffill_limit=3,          # same as the notebook: carry last value forward <= 3 h
    max_stale_hours=12,           # station silent longer than this at anchor -> "offline", no forecast
    min_stations_fraction=0.5,    # anchor = latest hour where >= 50% of stations reported PM2.5
    # --- dashboard history ---
    history_hours=168,            # 7 days
    pm25_interp_limit=12,         # linear-interpolate PM2.5 gaps up to 12 h; longer -> neighbour estimate
    aqi_interp_limit=6,
    other_interp_limit=3,         # sparse pollutants: only tiny gaps
    weather_interp_limit=6,
    min_pm25_real_fraction=0.25,  # < 25% real PM2.5 in the 7 days -> station shown as "insufficient data"
    min_pollutant_fraction=0.5,   # pollutant with < 50% coverage in the 7 days is hidden for that station
    allow_pm25_only_aqi=True,     # fill AQI gaps from PM2.5 sub-index (flagged 'p'); False -> leave null
    # --- alerts ---
    aqi_alert_threshold=100,      # same as AQI_ALERT_THRESHOLD in the notebook
    pollutant_thresholds={"pm25": 60, "pm10": 100},   # CPCB 24h standards, µg/m³ (add more once units are verified)
)

AQI_BANDS = [(0, 50, "Good"), (51, 100, "Satisfactory"), (101, 200, "Moderate"),
             (201, 300, "Poor"), (301, 400, "Very Poor"), (401, 500, "Severe")]


# ----------------------------------------------------------------------------- AQI helpers
def aqi_category(v):
    if v is None or not np.isfinite(v):
        return None
    for lo, hi, name in AQI_BANDS:
        if v <= hi:
            return name
    return "Severe"


def pm25_aqi(conc):
    """CPCB PM2.5 sub-index (µg/m³ -> 0-500). Works on scalars, arrays or Series."""
    c = np.asarray(conc, dtype=float)
    bp = [(0, 30, 0, 50), (30, 60, 51, 100), (60, 90, 101, 200),
          (90, 120, 201, 300), (120, 250, 301, 400), (250, 500, 401, 500)]
    out = np.full(c.shape, np.nan)
    for lo, hi, ilo, ihi in bp:
        m = (c >= lo) & (c <= hi) if lo == 0 else (c > lo) & (c <= hi)
        out[m] = (ihi - ilo) / (hi - lo) * (c[m] - lo) + ilo
    out[c > 500] = 500
    return pd.Series(out, index=conc.index) if isinstance(conc, pd.Series) else out


# ----------------------------------------------------------------------------- grid + features
def complete_hourly_grid(df):
    """One row per station per hour (missing hours become NaN rows)."""
    df = df.drop_duplicates(["location", "datetime"], keep="last")
    meta = df.groupby("location")[["latitude", "longitude"]].first()
    grid = pd.date_range(df["datetime"].min(), df["datetime"].max(), freq="h")
    idx = pd.MultiIndex.from_product([sorted(meta.index), grid], names=["location", "datetime"])
    out = df.set_index(["location", "datetime"]).reindex(idx)
    out[["latitude", "longitude"]] = meta.reindex(out.index.get_level_values(0)).to_numpy()
    return out.reset_index()


def _weights(stations):
    R = 6371.0
    lat, lon = np.radians(stations["latitude"].to_numpy()), np.radians(stations["longitude"].to_numpy())
    dlat, dlon = lat[:, None] - lat[None, :], lon[:, None] - lon[None, :]
    a = np.sin(dlat / 2) ** 2 + np.cos(lat[:, None]) * np.cos(lat[None, :]) * np.sin(dlon / 2) ** 2
    W = 1.0 / (2 * R * np.arcsin(np.sqrt(a)) + 1.0)
    np.fill_diagonal(W, 0.0)
    return W


def _add_spatial(df, W, loc_list):
    for col in ("pm25", "aqi"):
        pivot = df.pivot(index="datetime", columns="location", values=col)[loc_list]
        mask = pivot.notna().to_numpy(dtype=float)
        vals = pivot.fillna(0).to_numpy(dtype=float)
        with np.errstate(invalid="ignore", divide="ignore"):
            lag = (vals @ W.T) / (mask @ W.T)
        lag_df = pd.DataFrame(lag, index=pivot.index, columns=loc_list)
        lag_df = lag_df.rename_axis(columns="location").reset_index().melt(
            id_vars="datetime", var_name="location", value_name=f"spatial_{col}_neighbors")
        df = df.merge(lag_df, on=["datetime", "location"], how="left")
    return df


def _add_time_wind(df):
    hour, dow = df["datetime"].dt.hour, df["datetime"].dt.dayofweek
    df["hour_sin"], df["hour_cos"] = np.sin(2 * np.pi * hour / 24), np.cos(2 * np.pi * hour / 24)
    df["dow_sin"], df["dow_cos"] = np.sin(2 * np.pi * dow / 7), np.cos(2 * np.pi * dow / 7)
    rad = np.deg2rad(df["wind_direction_10m"])
    df["wind_direction_sin"], df["wind_direction_cos"] = np.sin(rad), np.cos(rad)
    return df


def _add_pm25_features(df):
    g = df.groupby("location")["pm25"]
    for k in (1, 3, 6, 12, 24):
        df[f"pm25_lag_{k}h"] = g.shift(k)
    for w in (3, 6, 24):
        df[f"pm25_rolling_mean_{w}h"] = g.transform(lambda s, w=w: s.rolling(w, min_periods=1).mean())
    df["pm25_rolling_std_6h"] = g.transform(lambda s: s.rolling(6, min_periods=2).std())
    return df


def find_anchor(df, cfg=CFG):
    """Common forecast start = latest hour at which enough stations reported PM2.5."""
    need = max(1, int(np.ceil(cfg["min_stations_fraction"] * df["location"].nunique())))
    cnt = df[df["pm25"].notna()].groupby("datetime")["location"].nunique()
    return cnt[cnt >= need].index.max()


def _stale_fill(df, status, cfg):
    """
    Station stopped earlier than the anchor (3 h < silence <= max_stale_hours):
    rebuild its PM2.5 up to the anchor as  last_value x (neighbours_now / neighbours_then).
    Keeps the station's own level, follows the trend of nearby stations. Flagged in `pm25_est`.
    """
    df["pm25_est"] = False
    for loc in status.index[status["status"] == "estimated"]:
        idx = df.index[df["location"] == loc]
        ts = df.loc[idx, "datetime"]
        pos0 = int((ts == status.loc[loc, "last_report"]).to_numpy().argmax())
        n = df.loc[idx, "spatial_pm25_neighbors"].ffill().to_numpy()
        v0 = df.loc[idx, "pm25_raw"].to_numpy()[pos0]
        n0 = n[pos0]
        if np.isfinite(n0) and n0 > 0:
            ratio = np.nan_to_num(np.clip(n / n0, 0.5, 2.0), nan=1.0)
        else:
            ratio = np.ones_like(n)
        after = np.arange(len(idx)) > pos0
        df.loc[idx[after], "pm25"] = (v0 * ratio)[after]
        df.loc[idx[after], "pm25_est"] = True
    return df


def prepare_model_frame(df_raw, cfg=CFG, for_inference=False):
    """
    Returns (frame, status, anchor).
      training  : for_inference=False -> same past-only cleaning as the notebook (+ hourly grid)
      inference : for_inference=True  -> also trims to the anchor and rebuilds stale stations
    """
    missing = [c for c in ["location", "datetime", "latitude", "longitude"] + FILL_COLS if c not in df_raw.columns]
    if missing:
        raise ValueError(f"Columns missing from dataset: {missing}")

    df = df_raw.copy()
    df["datetime"] = pd.to_datetime(df["datetime"]).dt.floor("h")
    anchor = find_anchor(df, cfg) if for_inference else df["datetime"].max()
    df = df[df["datetime"] <= anchor]
    df = complete_hourly_grid(df).sort_values(["location", "datetime"]).reset_index(drop=True)

    for c in FILL_COLS:                                   # untouched copies for "observed" flags
        df[f"{c}_raw"] = df[c]
    last_report = df[df["pm25"].notna()].groupby("location")["datetime"].max()

    g = df.groupby("location")
    for c in FILL_COLS:                                   # past-only, short carry-forward (as in notebook)
        df[c] = g[c].ffill(limit=cfg["model_ffill_limit"])
    for c in WEATHER_COLS:                                # weather is spatially smooth -> use other stations
        df[c] = df[c].fillna(df.groupby("datetime")[c].transform("median"))

    stations = df.groupby("location")[["latitude", "longitude"]].first().reset_index()
    loc_list = stations["location"].tolist()
    df = _add_spatial(df, _weights(stations), loc_list)

    hrs = (anchor - last_report.reindex(loc_list)).dt.total_seconds() / 3600
    status = pd.DataFrame({"last_report": last_report.reindex(loc_list), "hours_stale": hrs}, index=loc_list)
    status["status"] = np.select(
        [status["hours_stale"].isna() | (status["hours_stale"] > cfg["max_stale_hours"]),
         status["hours_stale"] <= cfg["model_ffill_limit"]],
        ["offline", "online"], default="estimated")

    if for_inference:
        df = _stale_fill(df, status, cfg)
    else:
        df["pm25_est"] = False
    df = _add_pm25_features(df)
    df = _add_time_wind(df)
    return df, status, anchor


def parity_report(df_raw, frame):
    """Compare recomputed lag/rolling/time features with the columns already in your CSV."""
    raw = df_raw.copy()
    raw["datetime"] = pd.to_datetime(raw["datetime"]).dt.floor("h")
    cols = [c for c in FEATURE_COLS if c.startswith(("pm25_lag", "pm25_rolling", "hour_", "dow_"))
            and c in raw.columns]
    m = raw[["location", "datetime"] + cols].merge(frame[["location", "datetime"] + cols],
                                                   on=["location", "datetime"], suffixes=("_csv", ""))
    for c in cols:
        both = m[f"{c}_csv"].notna() & m[c].notna()
        d = (m.loc[both, f"{c}_csv"] - m.loc[both, c]).abs()
        print(f"{c:26s} rows={both.sum():6d}  mean|diff|={d.mean():.6f}  share>1e-6={(d > 1e-6).mean():.2%}")


# ----------------------------------------------------------------------------- dashboard history
def _short_gap_interp(s, limit):
    """Linear-interpolate only gaps of <= `limit` hours (pandas would otherwise half-fill long gaps)."""
    filled = s.interpolate(limit_area="inside")
    isna = s.isna()
    gap_len = isna.groupby((~isna).cumsum()).transform("sum")
    return filled.mask(isna & (gap_len > limit))


def _circ_interp(obs, limit):
    r = np.deg2rad(obs)
    sn, cs = _short_gap_interp(np.sin(r), limit), _short_gap_interp(np.cos(r), limit)
    return pd.Series(np.rad2deg(np.arctan2(sn, cs)) % 360, index=obs.index).where(sn.notna())


def _num(x, nd=2):
    return None if x is None or not np.isfinite(x) else round(float(x), nd)


def _payload(values, flags, unit):
    return {"unit": unit, "values": [_num(v) for v in values],
            "flags": [f if np.isfinite(v) else None for v, f in zip(values, flags)]}


def _stats(obs, unit):
    v = obs.dropna()
    if v.empty:
        return None
    return {"min": _num(v.min()), "max": _num(v.max()), "mean": _num(v.mean()),
            "latest": _num(v.iloc[-1]), "latest_time": v.index[-1].isoformat(),
            "n_points": int(len(v)), "unit": unit}


def build_display(frame, status, anchor, cfg=CFG):
    win = frame[(frame["datetime"] > anchor - pd.Timedelta(hours=cfg["history_hours"]))
                & (frame["datetime"] <= anchor)]
    out = {}
    for loc, g in win.groupby("location", sort=True):
        g = g.set_index("datetime")
        st = status.loc[loc]
        rec = {"station": loc, "latitude": float(g["latitude"].iloc[0]), "longitude": float(g["longitude"].iloc[0]),
               "status": st["status"],
               "last_report": None if pd.isna(st["last_report"]) else st["last_report"].isoformat(),
               "hours_since_report": _num(st["hours_stale"], 1)}
        obs_pm = g["pm25_raw"]
        if obs_pm.notna().mean() < cfg["min_pm25_real_fraction"]:
            rec.update(status="insufficient_data", timestamps=[], pollutants={}, weather={}, stats={},
                       aqi_method=None, available_pollutants=[])
            out[loc] = rec
            continue

        rec["timestamps"] = [t.isoformat() for t in g.index]
        pollutants, weather, stats = {}, {}, {}

        # ---- PM2.5: always filled (short gaps interpolated, long gaps from neighbours) ----
        s = _short_gap_interp(obs_pm, cfg["pm25_interp_limit"])
        flag = pd.Series("o", index=g.index)
        flag[obs_pm.isna() & s.notna()] = "i"
        nb = g["spatial_pm25_neighbors"].ffill().bfill()
        ok = obs_pm.notna() & nb.notna() & (nb > 0)
        bias = float(np.clip((obs_pm[ok] / nb[ok]).median(), 0.5, 2.0)) if ok.sum() >= 6 else np.nan
        need = s.isna()
        s[need] = (nb * bias)[need]
        s = s.ffill().bfill()
        flag[need & s.notna()] = "e"
        if st["status"] == "offline" and pd.notna(st["last_report"]):
            dead = g.index > st["last_report"] + pd.Timedelta(hours=cfg["max_stale_hours"])
            s[dead] = np.nan                       # never invent data for a station that is truly dead
        pm25_filled = s.copy()
        pollutants["pm25"] = _payload(s.to_numpy(), flag.to_numpy(), UNITS["pm25"])
        stats["pm25"] = _stats(obs_pm, UNITS["pm25"])

        # ---- other pollutants: tiny gaps only, hide if coverage too low ----
        for c in OTHER_POLL:
            obs = g[f"{c}_raw"]
            s = _short_gap_interp(obs, cfg["other_interp_limit"])
            if s.notna().mean() < cfg["min_pollutant_fraction"]:
                continue
            fl = np.where(obs.notna(), "o", "i")
            pollutants[c] = _payload(s.to_numpy(), fl, UNITS[c])
            stats[c] = _stats(obs, UNITS[c])

        # ---- AQI ----
        obs = g["aqi_raw"]
        s = _short_gap_interp(obs, cfg["aqi_interp_limit"])
        real_cover = obs.notna().mean()
        flag = pd.Series(np.where(obs.notna(), "o", "i"), index=g.index)
        method = "cpcb_multi_pollutant" if real_cover >= cfg["min_pollutant_fraction"] else None
        if cfg["allow_pm25_only_aqi"]:
            derived = pm25_aqi(pm25_filled.rolling(24, min_periods=1).mean())
            need = s.isna() & pm25_filled.notna()
            s[need] = derived[need]
            flag[need] = "p"
            method = method or "pm25_based"
        if method is not None:
            pollutants["aqi"] = _payload(s.to_numpy(), flag.to_numpy(), "")
            keep = flag.isin(["o", "p"]) & s.notna()
            stats["aqi"] = _stats(s[keep], "")
        rec["aqi_method"] = method

        # ---- weather ----
        for c in WEATHER_COLS:
            obs = g[f"{c}_raw"]
            s = _circ_interp(obs, cfg["weather_interp_limit"]) if c == "wind_direction_10m" \
                else _short_gap_interp(obs, cfg["weather_interp_limit"])
            fl = pd.Series(np.where(obs.notna(), "o", "i"), index=g.index)
            fb = s.isna() & g[c].notna()
            s[fb] = g[c][fb]
            fl[fb] = "e"
            if s.notna().mean() < cfg["min_pollutant_fraction"]:
                continue
            weather[c] = _payload(s.to_numpy(), fl.to_numpy(), UNITS[c])
            stats[c] = _stats(obs, UNITS[c])

        rec.update(pollutants=pollutants, weather=weather, stats=stats,
                   available_pollutants=[p for p in POLLUTANTS if p in pollutants])
        out[loc] = rec
    return out


# ----------------------------------------------------------------------------- bundle (pickle)
def _target_col(key):
    var, h = key.rsplit("_", 1)
    return f"target_pm25_{h}" if var == "pm25" else f"target_{var}_{h}"


def save_bundle(path, models, X_full, df, train_mask, results_df, metadata, cfg=CFG):
    """Everything the backend needs to rebuild features and predict. Call once after training."""
    medians = {}
    for key in models:
        rows = df[_target_col(key)].notna() & train_mask
        medians[key] = X_full.loc[rows].median().to_dict()      # same rule as train_eval (train rows only)
    metrics = {}
    for r in results_df.to_dict("records"):
        t = r["target"]
        key = t.replace("target_", "", 1)
        metrics[key] = {"mae": float(r["model_mae"]), "baseline_mae": float(r["baseline_mae"]),
                        "r2": float(r["model_r2"]), "n_test_rows": int(r["n_test_rows"])}
    bundle = {"models": models, "x_columns": list(X_full.columns), "feature_cols": FEATURE_COLS,
              "train_medians": medians, "metrics": metrics, "metadata": metadata,
              "cfg": cfg, "version": 1}
    if path:                       # path=None -> keep the bundle in memory only (no pickle file)
        with open(path, "wb") as f:
            pickle.dump(bundle, f)
    return bundle


def load_bundle(path):
    with open(path, "rb") as f:
        return pickle.load(f)


# ----------------------------------------------------------------------------- forecast
def make_forecasts(bundle, frame, status, anchor, display, cfg):
    rows = frame[frame["datetime"] == anchor].set_index("location")
    ok = [loc for loc, d in display.items()
          if d["status"] in ("online", "estimated") and loc in rows.index and pd.notna(rows.loc[loc, "pm25"])]
    if not ok:
        return {}
    rows = rows.loc[ok].reset_index()
    xcols = bundle["x_columns"]
    X = rows[bundle["feature_cols"]].reset_index(drop=True)
    for c in xcols:
        if c.startswith("location_"):
            X[c] = (rows["location"].to_numpy() == c[len("location_"):]).astype(int)
    X = X[xcols]

    raw_pred = {}
    for key, model in bundle["models"].items():
        Xk = X.fillna(pd.Series(bundle["train_medians"][key]))
        raw_pred[key] = np.clip(model.predict(Xk), 0, None)

    def reliable(key):
        m = bundle["metrics"].get(key)
        return None if m is None else bool(m["mae"] < m["baseline_mae"])

    out = {}
    for i, loc in enumerate(ok):
        fc = {}
        for key in bundle["models"]:
            var, hs = key.rsplit("_", 1)
            h = int(hs[:-1])
            if var not in ("pm25", "aqi") and var not in display[loc]["available_pollutants"]:
                continue                                    # never forecast a pollutant the station doesn't measure
            if var == "aqi" and display[loc]["aqi_method"] != "cpcb_multi_pollutant":
                continue
            fc.setdefault(var, []).append({
                "horizon_h": h, "timestamp": (anchor + pd.Timedelta(hours=h)).isoformat(),
                "value": _num(raw_pred[key][i]), "unit": UNITS[var], "reliable": reliable(key)})
        if "aqi" not in fc and "pm25_6h" in raw_pred and cfg["allow_pm25_only_aqi"]:
            v = float(pm25_aqi(np.array([raw_pred["pm25_6h"][i]]))[0])
            fc["aqi"] = [{"horizon_h": 6, "timestamp": (anchor + pd.Timedelta(hours=6)).isoformat(),
                          "value": _num(v, 0), "unit": "", "reliable": reliable("pm25_6h"),
                          "method": "pm25_based"}]
        for var in fc:
            fc[var].sort(key=lambda p: p["horizon_h"])
        out[loc] = fc
    return out


def _alerts(fc, cfg):
    alerts = []
    for var, pts in fc.items():
        thr = cfg["aqi_alert_threshold"] if var == "aqi" else cfg["pollutant_thresholds"].get(var)
        if thr is None:
            continue
        for p in pts:
            if p["value"] is not None and p["value"] >= thr:
                alerts.append({"variable": var, "horizon_h": p["horizon_h"], "timestamp": p["timestamp"],
                               "value": p["value"], "threshold": thr, "reliable": p["reliable"],
                               "category": aqi_category(p["value"]) if var == "aqi" else None})
    return alerts


# ----------------------------------------------------------------------------- snapshot (JSON for React)
def _clean(o):
    if isinstance(o, dict):
        return {k: _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_clean(v) for v in o]
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating, float)):
        return None if not np.isfinite(o) else float(o)
    if isinstance(o, (pd.Timestamp,)):
        return o.isoformat()
    if isinstance(o, np.bool_):
        return bool(o)
    return o


def run_snapshot(bundle, raw_df, out_json=None, cfg=None):
    cfg = {**CFG, **(cfg or bundle.get("cfg", {}))}
    frame, status, anchor = prepare_model_frame(raw_df, cfg, for_inference=True)
    display = build_display(frame, status, anchor, cfg)
    forecasts = make_forecasts(bundle, frame, status, anchor, display, cfg)

    stations = []
    for loc, rec in display.items():
        fc = forecasts.get(loc, {})
        rec["forecast"] = fc
        rec["alerts"] = _alerts(fc, cfg)
        stations.append(rec)

    aqi6 = [(s["station"], p["value"]) for s in stations for p in s["forecast"].get("aqi", [])
            if p["horizon_h"] == 6 and p["value"] is not None]
    worst = max(aqi6, key=lambda t: t[1]) if aqi6 else None
    snapshot = {
        "meta": {"anchor_time": anchor.isoformat(), "history_hours": cfg["history_hours"],
                 "forecast_horizons_h": sorted({p["horizon_h"] for s in stations for v in s["forecast"].values() for p in v}),
                 "flags": {"o": "observed", "i": "interpolated", "e": "estimated from nearby stations",
                           "p": "AQI derived from PM2.5 only"},
                 "aqi_bands": [{"min": a, "max": b, "name": n} for a, b, n in AQI_BANDS],
                 "aqi_alert_threshold": cfg["aqi_alert_threshold"],
                 "trained_until": bundle.get("metadata", {}).get("cutoff_val")},
        "summary": {"stations_total": len(stations),
                    "online": sum(s["status"] == "online" for s in stations),
                    "estimated_start": sum(s["status"] == "estimated" for s in stations),
                    "offline": sum(s["status"] == "offline" for s in stations),
                    "insufficient_data": sum(s["status"] == "insufficient_data" for s in stations),
                    "stations_with_alert": sum(bool(s["alerts"]) for s in stations),
                    "highest_forecast_aqi_6h": None if worst is None else {"station": worst[0], "value": worst[1],
                                                                          "category": aqi_category(worst[1])}},
        "stations": stations,
    }
    snapshot = _clean(snapshot)
    if out_json:
        with open(out_json, "w") as f:
            json.dump(snapshot, f, allow_nan=False)
    return snapshot