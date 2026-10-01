from datetime import datetime
from typing import Dict, Any
import numpy as np
import pandas as pd
from config import get_settings
from app.services.external_api_service import get_external_api_service, ExternalAPIService


class DataService:
    def __init__(self):
        self.settings = get_settings()
        self.api_service: ExternalAPIService = get_external_api_service()
        self.csv_path = self.settings.csv_fallback_path

    def _get_time_features(self, dt: datetime) -> Dict[str, float]:
        hour = dt.hour
        dow = dt.weekday()
        return {
            "hour_sin": float(np.sin(2 * np.pi * hour / 24)),
            "hour_cos": float(np.cos(2 * np.pi * hour / 24)),
            "dow_sin": float(np.sin(2 * np.pi * dow / 7)),
            "dow_cos": float(np.cos(2 * np.pi * dow / 7)),
        }

    def _get_fallback_from_csv(self, location: str) -> Dict[str, Any]:
        """Reads the latest row from CSV fallback file."""
        df = pd.read_csv(self.csv_path)
        loc_df = df[df["location"].str.lower() == location.lower()]
        if loc_df.empty:
            loc_df = df  # default to last overall row if location string match fails
        
        last_row = loc_df.iloc[-1].to_dict()
        last_row["data_source"] = "csv_fallback"
        return last_row

    def get_feature_vector(self, location: str) -> Dict[str, Any]:
        """
        Attempts to construct live feature vector from APIs.
        Falls back gracefully to CSV if API call fails or rate-limits.
        """
        live_pm25 = self.api_service.get_live_aqi(location)
        live_weather = self.api_service.get_live_weather(location)

        # If live PM2.5 failed, fallback to CSV
        if live_pm25 is None:
            return self._get_fallback_from_csv(location)

        # Base weather defaults (if OpenWeather Key isn't set or fails, use seasonal Delhi defaults)
        weather = live_weather or {
            "temperature_2m": 28.0,
            "relative_humidity_2m": 60.0,
            "wind_speed_10m": 8.0,
            "wind_direction_10m": 180.0,
            "surface_pressure": 1010.0,
            "precipitation": 0.0,
            "temperature_change_3h": 0.0,
            "ventilation_index": 1500.0,
        }

        now = datetime.now()
        time_feats = self._get_time_features(now)

        # Attempt to contextualize lags using last known CSV entries for this location
        lags = {}
        try:
            df = pd.read_csv(self.csv_path)
            loc_df = df[df["location"].str.lower() == location.lower()]
            if not loc_df.empty:
                recent = loc_df["pm25"].dropna().iloc[-24:].tolist()
                recent.append(live_pm25)
                lags["pm25_lag_1h"] = float(recent[-2]) if len(recent) >= 2 else live_pm25
                lags["pm25_lag_3h"] = float(recent[-4]) if len(recent) >= 4 else live_pm25
                lags["pm25_lag_6h"] = float(recent[-7]) if len(recent) >= 7 else live_pm25
                lags["pm25_lag_12h"] = float(recent[-13]) if len(recent) >= 13 else live_pm25
                lags["pm25_lag_24h"] = float(recent[0]) if len(recent) >= 25 else live_pm25
                
                lags["pm25_rolling_mean_3h"] = float(np.mean(recent[-3:]))
                lags["pm25_rolling_mean_6h"] = float(np.mean(recent[-6:]))
                lags["pm25_rolling_mean_24h"] = float(np.mean(recent[-24:]))
                lags["pm25_rolling_std_6h"] = float(np.std(recent[-6:])) if len(recent) >= 6 else 0.0
        except Exception:
            pass

        # Fill any missing lag features with live_pm25 if historical lookup failed
        default_lags = {
            "pm25_lag_1h": live_pm25,
            "pm25_lag_3h": live_pm25,
            "pm25_lag_6h": live_pm25,
            "pm25_lag_12h": live_pm25,
            "pm25_lag_24h": live_pm25,
            "pm25_rolling_mean_3h": live_pm25,
            "pm25_rolling_mean_6h": live_pm25,
            "pm25_rolling_mean_24h": live_pm25,
            "pm25_rolling_std_6h": 0.0,
        }
        for k, v in default_lags.items():
            if k not in lags:
                lags[k] = v

        wind_rad = np.deg2rad(weather.get("wind_direction_10m", 0.0))
        wind_sin = float(np.sin(wind_rad))
        wind_cos = float(np.cos(wind_rad))

        feature_vector = {
            "location": location,
            "latitude": 28.6139,
            "longitude": 77.2090,
            "pm25": float(live_pm25),
            "temperature_2m": float(weather.get("temperature_2m", 28.0)),
            "relative_humidity_2m": float(weather.get("relative_humidity_2m", 60.0)),
            "wind_speed_10m": float(weather.get("wind_speed_10m", 8.0)),
            "wind_direction_sin": wind_sin,
            "wind_direction_cos": wind_cos,
            "surface_pressure": float(weather.get("surface_pressure", 1010.0)),
            "precipitation": float(weather.get("precipitation", 0.0)),
            "temperature_change_3h": float(weather.get("temperature_change_3h", 0.0)),
            "ventilation_index": float(weather.get("ventilation_index", 1500.0)),
            "spatial_pm25_neighbors": float(live_pm25),
            "spatial_aqi_neighbors": float(live_pm25),
            "data_source": "live_api",
            **time_feats,
            **lags
        }

        return feature_vector


def get_data_service() -> DataService:
    return DataService()
