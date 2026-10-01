import math
from config import get_settings


class WBGTService:
    def __init__(self):
        self.settings = get_settings()

    def calculate_wbgt(self, temp_c: float, humidity_rh: float) -> float:
        """
        Calculates Wet-Bulb Globe Temperature (WBGT) estimate using Stull (2011) formula
        for wet-bulb temperature combined with ambient temperature.
        Stull formula for T_wb (°C):
        T_wb = T * atan(0.151977 * (rh + 8.313659)^(1/2)) + atan(T + rh) - atan(rh - 1.676331)
               + 0.00391838 * (rh)^(3/2) * atan(0.023101 * rh) - 4.686035
        Simplified outdoor WBGT estimate: 0.7 * T_wb + 0.3 * T
        """
        T = temp_c
        rh = humidity_rh

        twb = (
            T * math.atan(0.151977 * math.pow(rh + 8.313659, 0.5))
            + math.atan(T + rh)
            - math.atan(rh - 1.676331)
            + 0.00391838 * math.pow(rh, 1.5) * math.atan(0.023101 * rh)
            - 4.686035
        )

        # WBGT approximation
        wbgt = 0.7 * twb + 0.3 * T
        return round(wbgt, 2)


def get_wbgt_service() -> WBGTService:
    return WBGTService()
