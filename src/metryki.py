import numpy as np
from dataclasses import dataclass

@dataclass
class Metryki:
    IAE: float
    ISE: float
    przeregulowanie: float
    czas_ustalania: float

def oblicz_metryki(t, r, y, settle_band=0.02):
    r = np.array(r)
    y = np.array(y)

    e = r - y
    IAE = np.trapz(np.abs(e), t)
    ISE = np.trapz(e ** 2, t)

    # --- Przeregulowanie [%] ---
    try:
        max_y = np.max(y)
        steady_state = r[-1]
        przeregulowanie = max(0.0, (max_y - steady_state) / (steady_state if abs(steady_state) > 1e-6 else 1.0) * 100.0)
    except Exception:
        przeregulowanie = 0.0

    # --- Czas ustalania [s] ---
    try:
        within_band = np.abs(y - steady_state) <= settle_band * steady_state
        last_within = np.where(within_band)[0]
        if len(last_within) > 0:
            czas_ustalania = t[last_within[-1]]
        else:
            czas_ustalania = t[-1]
    except Exception:
        czas_ustalania = t[-1]

    return Metryki(IAE, ISE, przeregulowanie, czas_ustalania)
