from typing import List, Dict, Any
from config import get_settings


class AlertService:
    def __init__(self):
        self.settings = get_settings()

    def generate_alerts(self, forecast_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        alerts = []
        for item in forecast_items:
            hour = item.get("hour")
            pm25 = item.get("pm25", 0.0)
            aqi = item.get("aqi", 0.0)
            wbgt = item.get("wbgt", 0.0)

            if pm25 >= self.settings.pm25_alert_threshold:
                alerts.append({
                    "hour": hour,
                    "type": "PM2.5_EXCEEDED",
                    "severity": "WARNING" if pm25 < 120 else "CRITICAL",
                    "message": f"Hour {hour}: PM2.5 elevated at {pm25} µg/m³ (Threshold: {self.settings.pm25_alert_threshold})"
                })

            if wbgt >= self.settings.wbgt_extreme_threshold:
                alerts.append({
                    "hour": hour,
                    "type": "HEAT_STRESS_EXTREME",
                    "severity": "CRITICAL",
                    "message": f"Hour {hour}: Extreme Heat Stress WBGT at {wbgt}°C (Threshold: {self.settings.wbgt_extreme_threshold}°C)"
                })
            elif wbgt >= self.settings.wbgt_high_threshold:
                alerts.append({
                    "hour": hour,
                    "type": "HEAT_STRESS_HIGH",
                    "severity": "WARNING",
                    "message": f"Hour {hour}: High Heat Stress WBGT at {wbgt}°C (Threshold: {self.settings.wbgt_high_threshold}°C)"
                })

        return alerts


def get_alert_service() -> AlertService:
    return AlertService()
