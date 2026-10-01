import time
from typing import Optional, Dict, Any
import httpx
from config import get_settings


class ExternalAPIService:
    def __init__(self):
        self.settings = get_settings()
        self._cache: Dict[str, Dict[str, Any]] = {}

    def _is_cache_valid(self, cache_key: str) -> bool:
        if cache_key not in self._cache:
            return False
        cached_time = self._cache[cache_key].get("timestamp", 0)
        return (time.time() - cached_time) < self.settings.api_cache_ttl_seconds

    def get_live_aqi(self, location: str) -> Optional[float]:
        """
        Fetches real-time PM2.5 (in µg/m³) from WAQI API.
        URL format: https://api.waqi.info/feed/{location}/?token={token}
        """
        cache_key = f"aqi_{location.lower()}"
        if self._is_cache_valid(cache_key):
            return self._cache[cache_key]["data"]

        token = self.settings.waqi_api_key
        url = f"https://api.waqi.info/feed/{location}/?token={token}"

        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.get(url)
                if response.status_code == 200:
                    payload = response.json()
                    if payload.get("status") == "ok":
                        iaqi = payload.get("data", {}).get("iaqi", {})
                        pm25_val = iaqi.get("pm25", {}).get("v")
                        if pm25_val is not None:
                            pm25_float = float(pm25_val)
                            self._cache[cache_key] = {
                                "timestamp": time.time(),
                                "data": pm25_float
                            }
                            return pm25_float
        except Exception:
            pass
        return None

    def get_live_weather(self, location: str) -> Optional[Dict[str, float]]:
        """
        Fetches real-time temp (°C), relative humidity (%), wind speed (km/h), and wind direction (deg)
        from OpenWeatherMap API.
        """
        cache_key = f"weather_{location.lower()}"
        if self._is_cache_valid(cache_key):
            return self._cache[cache_key]["data"]

        api_key = self.settings.openweather_api_key
        if not api_key:
            return None

        url = f"https://api.openweathermap.org/data/2.5/weather?q={location}&units=metric&appid={api_key}"

        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.get(url)
                if response.status_code == 200:
                    data = response.json()
                    main = data.get("main", {})
                    wind = data.get("wind", {})
                    
                    weather_dict = {
                        "temperature_2m": float(main.get("temp", 25.0)),
                        "relative_humidity_2m": float(main.get("humidity", 50.0)),
                        "wind_speed_10m": float(wind.get("speed", 1.0)) * 3.6,  # convert m/s to km/h
                        "wind_direction_10m": float(wind.get("deg", 0.0)),
                        "surface_pressure": float(main.get("pressure", 1013.25))
                    }
                    self._cache[cache_key] = {
                        "timestamp": time.time(),
                        "data": weather_dict
                    }
                    return weather_dict
        except Exception:
            pass
        return None


def get_external_api_service() -> ExternalAPIService:
    return ExternalAPIService()
