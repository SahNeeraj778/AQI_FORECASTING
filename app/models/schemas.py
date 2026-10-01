from typing import List, Optional
from pydantic import BaseModel, Field


class ForecastRequest(BaseModel):
    location: str = Field(default="Delhi", description="Location name or station identifier")

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "location": "Delhi"
                }
            ]
        }


class HourlyForecastItem(BaseModel):
    hour: int
    pm25: float
    aqi: float
    temperature: float
    humidity: float
    wbgt: float


class AlertItem(BaseModel):
    hour: int
    type: str
    severity: str
    message: str


class ForecastResponse(BaseModel):
    location: str
    data_source: str
    current_pm25: float
    current_temperature: float
    current_humidity: float
    forecast: List[HourlyForecastItem]
    alerts: List[AlertItem]

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "location": "Delhi",
                    "data_source": "live_api",
                    "current_pm25": 65.5,
                    "current_temperature": 29.5,
                    "current_humidity": 55.0,
                    "forecast": [
                        {
                            "hour": 1,
                            "pm25": 68.0,
                            "aqi": 127.0,
                            "temperature": 29.8,
                            "humidity": 54.0,
                            "wbgt": 26.5
                        }
                    ],
                    "alerts": [
                        {
                            "hour": 1,
                            "type": "PM2.5_EXCEEDED",
                            "severity": "WARNING",
                            "message": "Hour 1: PM2.5 elevated at 68.0 µg/m³"
                        }
                    ]
                }
            ]
        }
