import numpy as np
from dataclasses import dataclass

@dataclass
class Metryki:
    IAE: float
    ISE: float
    ITAE: float
    przeregulowanie: float      # [%] – zawsze liczba (dla r≈0 ustawiamy 0.0)
    czas_ustalania: float       # [s]
    czas_narastania: float      # [s] – dla r≈0: czas zaniku 90%→10%
    energia_sterowania: float

def _first_crossing_time(t, y, level, rising=True):
    for i in range(1, len(t)):
        if rising and (y[i-1] < level <= y[i]):
            a, b = y[i-1], y[i]
            return t[i-1] + (t[i]-t[i-1]) * (level - a) / (b - a)
        if (not rising) and (y[i-1] > level >= y[i]):
            a, b = y[i-1], y[i]
            return t[i-1] + (t[i]-t[i-1]) * (a - level) / (a - b)
    return None  # brak przecięcia

def oblicz_metryki(t, r, y, u=None, settle_band=0.02, hold_time=0.0):
    """
    Metryki z obsługą przypadków r≈0 (np. wahadło).
    - t_s: pasmo = 2% * max(skok zadania, max odchyłki odpowiedzi).
    - t_r: dla r!=0 klasyczne 10–90%; dla r≈0: czas zaniku 90%→10%.
    - Mp: dla r!=0 klasycznie; dla r≈0 ustawiamy 0.0 (zamiast NaN).
    """
    t = np.asarray(t); r = np.asarray(r); y = np.asarray(y)
    u = np.asarray(u) if u is not None else np.zeros_like(t)

    e = r - y
    IAE  = np.trapz(np.abs(e), t)
    ISE  = np.trapz(e**2, t)
    ITAE = np.trapz(t * np.abs(e), t)
    energia_sterowania = np.trapz(u**2, t)

    steady_state = r[-1]
    step_amp = abs(r[-1] - r[0])                    # amplituda skoku zadania
    resp_amp = np.max(np.abs(y - steady_state))     # maks. odchyłka odpowiedzi

    # --- Przeregulowanie [%] ---
    if step_amp > 1e-9:
        step_dir = np.sign(r[-1] - r[0]) or 1.0
        peak_dev = np.max(step_dir * (y - steady_state))
        przeregulowanie = max(0.0, 100.0 * peak_dev / step_amp)
    else:
        przeregulowanie = 0.0   # zdefiniowane jako 0 przy braku skoku

    # --- Czas ustalania [s] ---
    band_ref = step_amp if step_amp > 1e-9 else resp_amp
    tol = settle_band * (band_ref if band_ref > 1e-12 else 1.0)

    within = np.abs(y - steady_state) <= tol
    if hold_time and len(t) > 1:
        dt = np.mean(np.diff(t))
        n_hold = max(1, int(round(hold_time / dt)))
    else:
        n_hold = 1

    if n_hold == 1:
        last_bad_idxs = np.where(~within)[0]
        czas_ustalania = t[min(last_bad_idxs[-1] + 1, len(t)-1)] if last_bad_idxs.size else t[0]
    else:
        good = within.astype(int)
        consec = np.convolve(good, np.ones(n_hold, dtype=int), mode='same') >= n_hold
        last_bad_idxs = np.where(~consec)[0]
        czas_ustalania = t[min(last_bad_idxs[-1] + 1, len(t)-1)] if last_bad_idxs.size else t[0]

    # --- Czas narastania [s] ---
    if step_amp > 1e-9:
        y10 = r[0] + 0.10 * (r[-1] - r[0])
        y90 = r[0] + 0.90 * (r[-1] - r[0])
        rising = (r[-1] > r[0])
        t10 = _first_crossing_time(t, y, y10, rising=rising)
        t90 = _first_crossing_time(t, y, y90, rising=rising)
        if t10 is not None and t90 is not None and t90 >= t10:
            czas_narastania = t90 - t10
        else:
            czas_narastania = t[-1]  # bezpieczna wartość zamiast NaN
    else:
        # brak skoku zadania → czas zaniku |y-ss| z 90% do 10% wartości początkowej
        d0 = np.abs(y[0] - steady_state)
        if d0 > 1e-12:
            mag = np.abs(y - steady_state)
            idx90 = np.where(mag <= 0.9 * d0)[0]
            idx10 = np.where(mag <= 0.1 * d0)[0]
            if idx90.size and idx10.size:
                czas_narastania = t[idx10[0]] - t[idx90[0]]
            else:
                czas_narastania = t[-1]
        else:
            czas_narastania = 0.0

    return Metryki(
        IAE=IAE, ISE=ISE, ITAE=ITAE,
        przeregulowanie=przeregulowanie,
        czas_ustalania=czas_ustalania,
        czas_narastania=czas_narastania,
        energia_sterowania=energia_sterowania
    )
