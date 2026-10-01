import os
import pickle
from typing import Dict, Any, List
import numpy as np
import pandas as pd
from config import get_settings


class ModelService:
    def __init__(self):
        self.settings = get_settings()
        self.bundle_path = self.settings.model_bundle_path
        self.bundle = self._load_bundle()

    def _load_bundle(self) -> Dict[str, Any]:
        if os.path.exists(self.bundle_path):
            try:
                with open(self.bundle_path, "rb") as f:
                    return pickle.load(f)
            except Exception:
                pass
        return {}

    def predict_24h_forecast(self, features: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generates 24-hour predictions for PM2.5 and calculated AQI.
        If pre-trained model bundle is present, it invokes XGBoost models.
        Otherwise, uses an autoregressive decay-trend heuristic model baseline.
        """
        base_pm25 = float(features.get("pm25", 50.0))
        temp = float(features.get("temperature_2m", 28.0))
        rh = float(features.get("relative_humidity_2m", 60.0))

        predictions = []

        if self.bundle and "models" in self.bundle:
            # Use trained model pipeline if available
            feature_cols = self.bundle.get("feature_cols", [])
            df_feat = pd.DataFrame([features])
            for col in feature_cols:
                if col not in df_feat:
                    df_feat[col] = 0.0
            
            X = df_feat[feature_cols]
            models = self.bundle["models"]
            
            for h in range(1, 25):
                key = f"pm25_{h}h"
                if key in models:
                    pred_pm25 = float(models[key].predict(X)[0])
                else:
                    # fallback trend
                    pred_pm25 = base_pm25 * (1 + 0.01 * np.sin(h / 3.0))
                
                # CPCB AQI calculation helper for PM2.5
                aqi_val = self._pm25_to_aqi(pred_pm25)
                predictions.append({
                    "hour": h,
                    "pm25": round(pred_pm25, 2),
                    "aqi": round(aqi_val, 2),
                    "temperature": round(temp + 0.2 * np.sin(h / 4.0), 2),
                    "humidity": round(rh - 0.3 * np.sin(h / 4.0), 2)
                })
        else:
            # Diurnal baseline fallback
            for h in range(1, 25):
                pred_pm25 = base_pm25 * (1.0 + 0.15 * np.sin(2 * np.pi * (h - 6) / 24))
                pred_pm25 = max(5.0, pred_pm25)
                aqi_val = self._pm25_to_aqi(pred_pm25)
                predictions.append({
                    "hour": h,
                    "pm25": round(pred_pm25, 2),
                    "aqi": round(aqi_val, 2),
                    "temperature": round(temp + 2.0 * np.sin(2 * np.pi * (h - 9) / 24), 2),
                    "humidity": round(max(10.0, min(100.0, rh - 5.0 * np.sin(2 * np.pi * (h - 9) / 24))), 2)
                })

        return predictions

    def _pm25_to_aqi(self, c: float) -> float:
        bp = [
            (0, 30, 0, 50),
            (30, 60, 51, 100),
            (60, 90, 101, 200),
            (90, 120, 201, 300),
            (120, 250, 301, 400),
            (250, 500, 401, 500)
        ]
        if c > 500:
            return 500.0
        for lo, hi, ilo, ihi in bp:
            if (lo == 0 and c >= lo and c <= hi) or (lo > 0 and c > lo and c <= hi):
                return (ihi - ilo) / (hi - lo) * (c - lo) + ilo
        return c


def get_model_service() -> ModelService:
    return ModelService()
