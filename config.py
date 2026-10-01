import os
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "AQI & Weather Coupled Forecasting Backend"
    environment: str = "development"
    debug: bool = True

    # External API Keys & TTL
    waqi_api_key: str = "demo"
    openweather_api_key: str = ""
    api_cache_ttl_seconds: int = 300

    # Data & Model File Paths
    csv_fallback_path: str = "/home/sourav/Cosmos/Hackathon/ml/data/delhi_pm25_features.csv"
    model_bundle_path: str = "ml/model/aqi_model.pkl"

    # Thresholds for alerts
    pm25_alert_threshold: float = 60.0
    aqi_alert_threshold: float = 100.0
    wbgt_high_threshold: float = 28.0
    wbgt_extreme_threshold: float = 31.0

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
