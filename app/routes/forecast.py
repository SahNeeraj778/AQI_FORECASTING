from typing import Optional, List
from fastapi import APIRouter, Depends
from app.models.schemas import ForecastRequest, ForecastResponse, HourlyForecastItem, AlertItem
from app.services.data_service import get_data_service, DataService
from app.services.model_service import get_model_service, ModelService
from app.services.wbgt_service import get_wbgt_service, WBGTService
from app.services.alert_service import get_alert_service, AlertService

router = APIRouter(prefix="/api/v1", tags=["Forecast"])


@router.api_route("/forecast", methods=["GET", "POST"], response_model=ForecastResponse)
def get_forecast(
    request: Optional[ForecastRequest] = None,
    location: Optional[str] = "Delhi",
    data_service: DataService = Depends(get_data_service),
    model_service: ModelService = Depends(get_model_service),
    wbgt_service: WBGTService = Depends(get_wbgt_service),
    alert_service: AlertService = Depends(get_alert_service)
) -> ForecastResponse:
    """
    Real-time AQI and Weather coupled forecast endpoint (supports GET & POST).
    """
    target_location = request.location if (request and request.location) else (location or "Delhi")
    features = data_service.get_feature_vector(target_location)
    data_source = features.get("data_source", "unknown")
    current_pm25 = float(features.get("pm25", 0.0))
    current_temp = float(features.get("temperature_2m", 28.0))
    current_humidity = float(features.get("relative_humidity_2m", 60.0))

    # 2. Get 24-hour predictions
    raw_predictions = model_service.predict_24h_forecast(features)

    # 3. Calculate dynamic WBGT for each forecast hour
    forecast_items = []
    for item in raw_predictions:
        h_temp = item.get("temperature", current_temp)
        h_humidity = item.get("humidity", current_humidity)
        wbgt_val = wbgt_service.calculate_wbgt(h_temp, h_humidity)
        
        forecast_item = {
            "hour": item.get("hour"),
            "pm25": item.get("pm25"),
            "aqi": item.get("aqi"),
            "temperature": h_temp,
            "humidity": h_humidity,
            "wbgt": wbgt_val
        }
        forecast_items.append(forecast_item)

    # 4. Generate dynamic alerts
    alerts = alert_service.generate_alerts(forecast_items)

    # 5. Return typed response
    return ForecastResponse(
        location=target_location,
        data_source=data_source,
        current_pm25=current_pm25,
        current_temperature=current_temp,
        current_humidity=current_humidity,
        forecast=[HourlyForecastItem(**item) for item in forecast_items],
        alerts=[AlertItem(**alert) for alert in alerts]
    )
