# src/metryki.py
from __future__ import annotations
from dataclasses import dataclass
import numpy as np


@dataclass
class Metryki:
    IAE: float
    ISE: float
    ITAE: float
    przeregulowanie: float        # [%]
    czas_ustalania: float         # [s]
    czas_narastania: float        # [s] 10-90%
    uchyb_ustalony: float
    procent_czasu_w_saturacji: float  # [%]
    ymin: float
    ymax: float
    umin: float
    umax: float


def _overshoot_percent(y: np.ndarray, ss: float) -> float:
    if ss == 0:
        return 0.0
    peak = np.max(y)
    if ss > 0:
        return max(0.0, (peak - ss) / abs(ss) * 100.0)
    else:
        trough = np.min(y)
        return max(0.0, (ss - trough) / abs(ss) * 100.0)


def oblicz_metryki(
    t: list[float] | np.ndarray,
    r: list[float] | np.ndarray,
    y: list[float] | np.ndarray,
    u: list[float] | np.ndarray,
    settle_band: float = 0.02  # +/-2% of steady-state
) -> Metryki:
    """
    Compute standard time/frequency metrics from step response.
    Assumptions:
        - r is constant (step) after initial moment.
        - y, u are 1D lists/arrays.
    """
    t = np.asarray(t, dtype=float)
    r = np.asarray(r, dtype=float)
    y = np.asarray(y, dtype=float)
    u = np.asarray(u, dtype=float)

    dt = np.mean(np.diff(t)) if len(t) > 1 else 1.0
    steady_state = r[-1] if len(r) else 1.0
    e = r - y

    IAE = np.trapz(np.abs(e), t)
    ISE = np.trapz(e ** 2, t)
    ITAE = np.trapz(t * np.abs(e), t)

    # Overshoot in percent of steady-state
    przereg = _overshoot_percent(y, steady_state)

    # Settling time = last time index for which |y - ss| > band, then next sample
    try:
        band = settle_band * max(abs(steady_state), 1e-9)
        outside = np.where(np.abs(y - steady_state) > band)[0]
        if len(outside) == 0:
            czas_ust = 0.0
        else:
            last_out = outside[-1]
            czas_ust = t[last_out + 1] if (last_out + 1) < len(t) else t[-1]
    except Exception:
        czas_ust = t[-1] if len(t) else 0.0

    # Rise time (10% -> 90% of steady-state)
    try:
        if abs(steady_state) > 1e-9:
            y10 = 0.1 * steady_state
            y90 = 0.9 * steady_state
            if steady_state > 0:
                i10 = np.where(y >= y10)[0]
                i90 = np.where(y >= y90)[0]
            else:
                i10 = np.where(y <= y10)[0]
                i90 = np.where(y <= y90)[0]
            t10 = t[i10[0]] if len(i10) else t[0]
            t90 = t[i90[0]] if len(i90) else t[-1]
            czas_nar = max(0.0, t90 - t10)
        else:
            czas_nar = 0.0
    except Exception:
        czas_nar = t[-1] if len(t) else 0.0

    uchyb_ss = float(e[-1]) if len(e) else 0.0

    # Percentage of time in saturation (assume umin/umax are min/max observed)
    umin_obs = float(np.min(u)) if len(u) else 0.0
    umax_obs = float(np.max(u)) if len(u) else 0.0
    eps = 1e-9
    sat_mask = (np.isclose(u, umin_obs, atol=eps) | np.isclose(u, umax_obs, atol=eps))
    sat_percent = 100.0 * (np.sum(sat_mask) / len(u)) if len(u) else 0.0

    return Metryki(
        IAE=float(IAE),
        ISE=float(ISE),
        ITAE=float(ITAE),
        przeregulowanie=float(przereg),
        czas_ustalania=float(czas_ust),
        czas_narastania=float(czas_nar),
        uchyb_ustalony=float(uchyb_ss),
        procent_czasu_w_saturacji=float(sat_percent),
        ymin=float(np.min(y) if len(y) else 0.0),
        ymax=float(np.max(y) if len(y) else 0.0),
        umin=umin_obs,
        umax=umax_obs,
    )
