# src/ziegler_nichols.py
from __future__ import annotations
import numpy as np

# Importy tak, by działało i jako pakiet i jako moduł uruchamiany bez pakietu
try:
    from .modele.zbiornik_1rz import Zbiornik_1rz
    from .modele.dwa_zbiorniki import Dwa_zbiorniki
    from .modele.wahadlo_odwrocone import Wahadlo_odwrocone
    from .regulatory.regulator_p import regulator_p as RegP
except Exception:
    from src.modele.zbiornik_1rz import Zbiornik_1rz
    from src.modele.dwa_zbiorniki import Dwa_zbiorniki
    from src.modele.wahadlo_odwrocone import Wahadlo_odwrocone
    from src.regulatory.regulator_p import regulator_p as RegP


def _make_model(model_key: str):
    cls = {
        "zbiornik_1rz": Zbiornik_1rz,
        "dwa_zbiorniki": Dwa_zbiorniki,
        "wahadlo_odwrocone": Wahadlo_odwrocone,
    }.get(model_key, Zbiornik_1rz)
    return cls()


def _simulate_p(model, Kp: float, T: float = 120.0, r_value: float = 1.0):
    dt = float(getattr(model, "dt", 0.05))
    N = int(T / dt)
    reg = RegP(Kp=Kp, Kr=1.0, dt=dt, umin=0.0, umax=1.0)
    y = np.zeros(N)
    u = np.zeros(N)
    r = float(r_value)
    for k in range(1, N):
        u[k] = reg.update(r, y[k - 1])
        y[k] = model.step(u[k])
    t = np.arange(N) * dt
    return t, y, u


def _find_peaks(y: np.ndarray):
    peaks = []
    for k in range(1, len(y) - 1):
        if y[k] > y[k - 1] and y[k] > y[k + 1]:
            peaks.append(k)
    return np.asarray(peaks, dtype=int)


def _estimate_Tu_from_peaks(t: np.ndarray, peaks: np.ndarray):
    if len(peaks) < 2:
        return None
    periods = np.diff(t[peaks])
    if len(periods) >= 3:
        periods = periods[-3:]
    return float(np.mean(periods)) if len(periods) else None


def _is_sustained(y: np.ndarray, peaks: np.ndarray, tol: float = 0.25):
    """
    'Oscylacje graniczne' ≈ amplituda kolejnych maksimów jest podobna
    (brak silnego tłumienia lub narastania). Wymagamy ≥3 pików.
    """
    if len(peaks) < 3:
        return False
    amps = np.maximum(np.abs(y[peaks][-3:]), 1e-9)
    ratios = amps[1:] / amps[:-1]
    return np.all((ratios > 1 - tol) & (ratios < 1 + tol))


def _search_Ku(model_key: str, T: float = 120.0):
    # Przeszukiwanie logarytmiczne Kp
    grid = np.geomspace(0.05, 200.0, 40)
    for K in grid:
        model = _make_model(model_key)  # świeży model dla każdej próby
        t, y, _ = _simulate_p(model, float(K), T=T)
        peaks = _find_peaks(y)
        if _is_sustained(y, peaks):
            Tu = _estimate_Tu_from_peaks(t, peaks)
            if Tu and Tu > 0:
                return float(K), float(Tu)
    return None, None


def policz_zn(regulator: str, model_key: str):
    """
    Zwraca parametry wg klasycznych reguł Ziegler–Nichols w formacie:
      {"Kp": ..., "Ti": ..., "Td": ...}
    albo None, gdy nie znaleziono (Ku, Tu) prostym skanem regulatora P.
    """
    Ku, Tu = _search_Ku(model_key)
    if not Ku or not Tu:
        return None

    reg = (regulator or "").lower()
    if reg == "regulator_pid":
        Kp = 0.6 * Ku
        Ti = 0.5 * Tu
        Td = 0.125 * Tu
    elif reg == "regulator_pi":
        Kp = 0.45 * Ku
        Ti = 0.83 * Tu
        Td = 0.0
    elif reg == "regulator_p":
        Kp = 0.5 * Ku
        Ti = 0.0
        Td = 0.0
    else:
        # Dla PD nie ma klasycznej tabeli ZN
        return None

    return {
        "Kp": round(float(Kp), 6),
        "Ti": round(float(Ti), 6),
        "Td": round(float(Td), 6),
    }
