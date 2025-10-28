import numpy as np
from dataclasses import dataclass

@dataclass
class Metryki:
    IAE: float  # Integral of Absolute Error
    ISE: float  # Integral of Squared Error
    ITAE: float  # Integral of Time-weighted Absolute Error
    przeregulowanie: float  # Overshoot [%]
    czas_ustalania: float  # Settling time [s]
    czas_narastania: float  # Rise time [s]
    energia_sterowania: float  # Control energy

def oblicz_metryki(t, r, y, u=None, settle_band=0.02):
    """Oblicza metryki jakości regulacji.
    
    Args:
        t: wektor czasu [s]
        r: wektor wartości zadanej
        y: wektor odpowiedzi układu
        u: wektor sygnału sterującego (opcjonalny)
        settle_band: pasmo ustalania (±2% domyślnie)
    """
    t = np.array(t)
    r = np.array(r)
    y = np.array(y)
    u = np.array(u) if u is not None else np.zeros_like(t)

    e = r - y
    IAE = np.trapz(np.abs(e), t)
    ISE = np.trapz(e ** 2, t)
    ITAE = np.trapz(t * np.abs(e), t)  # Time-weighted IAE
    
    steady_state = r[-1]
    
    # --- Przeregulowanie [%] ---
    try:
        max_y = np.max(y)
        przeregulowanie = max(0.0, (max_y - steady_state) / (steady_state if abs(steady_state) > 1e-6 else 1.0) * 100.0)
    except Exception:
        przeregulowanie = 0.0

    # --- Czas ustalania [s] ---
    try:
        within_band = np.abs(y - steady_state) <= settle_band * abs(steady_state)
        last_within = np.where(within_band)[0]
        if len(last_within) > 0:
            czas_ustalania = t[last_within[0]]  # First time entering the band
            for i in range(len(last_within)-1):
                if last_within[i+1] - last_within[i] > 1:  # Gap found
                    czas_ustalania = t[last_within[i+1]]  # Update to later entry
        else:
            czas_ustalania = t[-1]
    except Exception:
        czas_ustalania = t[-1]

    # --- Czas narastania [s] ---
    try:
        if abs(steady_state) > 1e-6:
            t_10 = np.interp(0.1 * steady_state, y, t)
            t_90 = np.interp(0.9 * steady_state, y, t)
            czas_narastania = t_90 - t_10
        else:
            czas_narastania = 0.0
    except Exception:
        czas_narastania = t[-1]

    # --- Energia sterowania ---
    energia_sterowania = np.trapz(u ** 2, t)

    return Metryki(
        IAE=IAE,
        ISE=ISE,
        ITAE=ITAE,
        przeregulowanie=przeregulowanie,
        czas_ustalania=czas_ustalania,
        czas_narastania=czas_narastania,
        energia_sterowania=energia_sterowania
    )
