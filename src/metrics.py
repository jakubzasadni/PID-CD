# src/metrics.py
# Control quality metrics: rise time, settling time, overshoot, IAE, ISE

from dataclasses import dataclass
from typing import List, Tuple
import math

@dataclass
class StepMetrics:
    rise_time: float
    settling_time: float
    overshoot_pct: float
    iae: float
    ise: float

def compute_metrics(t: List[float], r: List[float], y: List[float], e: List[float],
                    settle_band: float = 0.02) -> StepMetrics:
    assert len(t) == len(y) == len(e) == len(r)
    dt = t[1] - t[0] if len(t) > 1 else 0.0
    r_final = r[-1] if len(r) else 1.0

    # Rise time (10% -> 90% of final value)
    y10 = 0.1 * r_final
    y90 = 0.9 * r_final
    t10 = next((t[i] for i, yy in enumerate(y) if yy >= y10), math.nan)
    t90 = next((t[i] for i, yy in enumerate(y) if yy >= y90), math.nan)
    rise_time = (t90 - t10) if (not math.isnan(t10) and not math.isnan(t90) and t90 >= t10) else math.nan

    # Overshoot
    y_max = max(y) if len(y) else 0.0
    overshoot_pct = max(0.0, (y_max - r_final) / max(1e-9, r_final) * 100.0)

    # Settling time (within +/- settle_band of final value)
    lower = (1 - settle_band) * r_final
    upper = (1 + settle_band) * r_final
    settling_time = math.nan
    for i in range(len(y)-1, -1, -1):
        if y[i] < lower or y[i] > upper:
            settling_time = t[i+1] if i+1 < len(t) else t[-1]
            break
    if math.isnan(settling_time):
        settling_time = 0.0

    # IAE / ISE
    iae = sum(abs(err) * dt for err in e)
    ise = sum((err * err) * dt for err in e)

    return StepMetrics(rise_time, settling_time, overshoot_pct, iae, ise)
