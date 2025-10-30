import numpy as np
from dataclasses import dataclass

@dataclass
class Metryki:
    IAE: float
    ISE: float
    ITAE: float
    przeregulowanie: float   # Overshoot [%], NaN gdy nieokreślone
    czas_ustalania: float    # Settling time [s]
    czas_narastania: float   # Rise time [s] (dla r=0: czas zaniku 90→10%)
    energia_sterowania: float

def _first_crossing_time(t, y, level, rising=True):
    """Liniowa interpolacja czasu pierwszego przekroczenia 'level'."""
    for i in range(1, len(t)):
        if rising and (y[i-1] < level <= y[i]):
            # linear interp
            a, b = y[i-1], y[i]
            return t[i-1] + (t[i]-t[i-1]) * (level - a) / (b - a)
        if (not rising) and (y[i-1] > level >= y[i]):
            a, b = y[i-1], y[i]
            return t[i-1] + (t[i]-t[i-1]) * (a - level) / (a - b)
    return np.nan

def oblicz_metryki(t, r, y, u=None, settle_band=0.02, hold_time=0.0):
    """
    Liczy metryki jakości regulacji.
    - Dla zwykłego skoku r: czasy 10–90% liczone względem skoku zadania.
    - Gdy skok zadania ~0 (np. wahadło): pasmo i czasy liczone względem
      maks. odchyłki od stanu ustalonego (zanik 90%→10%).
    """
    t = np.asarray(t); r = np.asarray(r); y = np.asarray(y)
    u = np.asarray(u) if u is not None else np.zeros_like(t)

    e = r - y
    IAE  = np.trapz(np.abs(e), t)
    ISE  = np.trapz(e**2, t)
    ITAE = np.trapz(t * np.abs(e), t)
    energia_sterowania = np.trapz(u**2, t)

    steady_state = r[-1]
    step_amp = abs(r[-1] - r[0])                  # amplituda skoku zadania
    resp_amp = np.max(np.abs(y - steady_state))   # maksymalna odchyłka odpowiedzi

    # --- Przeregulowanie ---
    if step_amp > 1e-9:
        step_dir = np.sign(r[-1] - r[0]) or 1.0
        peak_dev = np.max(step_dir * (y - steady_state))  # max powyżej stanu ustalonego dla danego kierunku
        przeregulowanie = max(0.0, 100.0 * peak_dev / step_amp)
    else:
        przeregulowanie = float('nan')  # brak sensownej definicji dla r≈0

    # --- Czas ustalania ---
    # tolerancja: 2% * (skok zadania) lub – gdy brak skoku – 2% * max odchyłki
    band_ref = step_amp if step_amp > 1e-9 else resp_amp
    tol = settle_band * (band_ref if band_ref > 1e-12 else 1.0)

    within = np.abs(y - steady_state) <= tol
    if hold_time and len(t) > 1:  # opcjonalny warunek podtrzymania
        dt = np.mean(np.diff(t))
        n_hold = max(1, int(round(hold_time / dt)))
    else:
        n_hold = 1

    # znajdź najpóźniejsze naruszenie pasma; t_s = chwila po nim
    if not np.all(within):
        if n_hold == 1:
            last_bad = np.max(np.where(~within)[0])
            czas_ustalania = t[min(last_bad + 1, len(t)-1)]
        else:
            good = within.astype(int)
            # splot do warunku "n_hold kolejnych próbek w paśmie"
            win = np.ones(n_hold, dtype=int)
            consec = np.convolve(good, win, mode='same') >= n_hold
            last_bad = np.max(np.where(~consec)[0]) if not np.all(consec) else -1
            czas_ustalania = t[min(last_bad + 1, len(t)-1)]
    else:
        czas_ustalania = t[0]

    # --- Czas narastania ---
    if step_amp > 1e-9:
        # klasyczne 10–90% skoku zadania
        y10 = r[0] + 0.10 * (r[-1] - r[0])
        y90 = r[0] + 0.90 * (r[-1] - r[0])
        rising = (r[-1] > r[0])
        t10 = _first_crossing_time(t, y, y10, rising=rising)
        t90 = _first_crossing_time(t, y, y90, rising=rising)
        czas_narastania = (t90 - t10) if np.isfinite(t10) and np.isfinite(t90) else float('nan')
    else:
        # brak skoku zadania → czas zaniku |y-ss| z 90% do 10% wartości początkowej
        d0 = np.abs(y[0] - steady_state)
        if d0 > 1e-12:
            mag = np.abs(y - steady_state)
            idx90 = np.argmax(mag <= 0.9 * d0)
            idx10 = np.argmax(mag <= 0.1 * d0)
            czas_narastania = (t[idx10] - t[idx90]) if (idx90 > 0 and idx10 > 0) else float('nan')
        else:
            czas_narastania = float('nan')

    return Metryki(
        IAE=IAE, ISE=ISE, ITAE=ITAE,
        przeregulowanie=przeregulowanie,
        czas_ustalania=czas_ustalania,
        czas_narastania=czas_narastania,
        energia_sterowania=energia_sterowania
    )
