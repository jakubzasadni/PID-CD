# src/strojenie/wykonaj_strojenie.py
from __future__ import annotations
import numpy as np

# --- resilient imports for package layout ---
try:
    # when called as package: src.strojenie.wykonaj_strojenie
    from .przeszukiwanie_siatki import przeszukiwanie_siatki
    from .optymalizacja_numeryczna import optymalizuj_podstawowy as optymalizacja
except ImportError:
    # fallback if executed differently
    from src.strojenie.przeszukiwanie_siatki import przeszukiwanie_siatki
    from src.strojenie.optymalizacja_numeryczna import optymalizuj_podstawowy as optymalizacja

from src.modele.zbiornik_1rz import Zbiornik_1rz
from src.modele.dwa_zbiorniki import Dwa_zbiorniki
from src.modele.wahadlo_odwrocone import Wahadlo_odwrocone

from src.regulatory.regulator_p import Regulator_P
from src.regulatory.regulator_pi import Regulator_PI
from src.regulatory.regulator_pd import Regulator_PD
from src.regulatory.regulator_pid import Regulator_PID

from src.metryki import oblicz_metryki


# ---------- simulation helper ----------
def _symuluj(model, regulator, T: float = 120.0, r_value: float = 1.0):
    dt = float(getattr(model, "dt", 0.05))
    N = int(np.ceil(T / dt))
    t = np.zeros(N)
    r = np.full(N, r_value, dtype=float)
    y = np.zeros(N)
    u = np.zeros(N)
    # initial output if model exposes it
    y[0] = float(getattr(model, "y", 0.0))
    for k in range(1, N):
        uk = regulator.update(r[k - 1], y[k - 1])
        yk = model.step(uk)
        t[k] = k * dt
        y[k] = yk
        u[k] = uk
    m = oblicz_metryki(t, r, y, u, settle_band=0.02)
    return m, (t, r, y, u)


# ---------- objective functions (IAE + mild penalties) ----------
def _J(metrics):
    return metrics.IAE + 0.1 * metrics.czas_ustalania + 0.05 * max(0.0, metrics.przeregulowanie - 5.0)


def cel_P(Kp: float, model_cls=Zbiornik_1rz, T: float = 120.0) -> float:
    model = model_cls()
    reg = Regulator_P(kp=Kp, dt=model.dt, umin=0.0, umax=1.0)
    m, _ = _symuluj(model, reg, T=T, r_value=1.0)
    return _J(m)


def cel_PI(Kp: float, Ti: float, model_cls=Zbiornik_1rz, T: float = 120.0) -> float:
    model = model_cls()
    reg = Regulator_PI(kp=Kp, ti=Ti, tt=max(Ti / 2.0, 1.0), dt=model.dt, umin=0.0, umax=1.0)
    m, _ = _symuluj(model, reg, T=T, r_value=1.0)
    return _J(m)


def cel_PD(Kp: float, Td: float, model_cls=Dwa_zbiorniki, Kr: float = 1.0, T: float = 120.0) -> float:
    model = model_cls()
    reg = Regulator_PD(kp=Kp, td=Td, Kr=Kr, dt=model.dt, umin=0.0, umax=1.0)
    m, _ = _symuluj(model, reg, T=T, r_value=1.0)
    return _J(m)


def cel_PID(Kp: float, Ti: float, Td: float, model_cls=Dwa_zbiorniki, T: float = 120.0) -> float:
    model = model_cls()
    reg = Regulator_PID(kp=Kp, ti=Ti, td=Td, tt=max(Ti / 2.0, 1.0), beta=0.9, dt=model.dt, umin=0.0, umax=1.0)
    m, _ = _symuluj(model, reg, T=T, r_value=1.0)
    return _J(m)


# ---------- grids ----------
def siatka_P():
    return {"Kp": np.linspace(0.1, 8.0, 40)}


def siatka_PI():
    return {"Kp": np.linspace(0.3, 6.0, 30), "Ti": np.linspace(4.0, 30.0, 40)}


def siatka_PD():
    return {"Kp": np.linspace(0.3, 6.0, 30), "Td": np.linspace(0.1, 6.0, 30)}


def siatka_PID():
    return {
        "Kp": np.linspace(0.3, 6.0, 26),
        "Ti": np.linspace(6.0, 30.0, 25),
        "Td": np.linspace(0.2, 6.0, 25),
    }


# ---------- public API wrappers ----------
def strojenie_P_grid(model_cls=Zbiornik_1rz, T: float = 120.0):
    return przeszukiwanie_siatki(
        siatki=siatka_P(),
        funkcja_celu=lambda Kp: cel_P(Kp, model_cls=model_cls, T=T),
    )


def strojenie_PI_grid(model_cls=Zbiornik_1rz, T: float = 120.0):
    return przeszukiwanie_siatki(
        siatki=siatka_PI(),
        funkcja_celu=lambda Kp, Ti: cel_PI(Kp, Ti, model_cls=model_cls, T=T),
    )


def strojenie_PD_grid(model_cls=Dwa_zbiorniki, Kr: float = 1.0, T: float = 120.0):
    return przeszukiwanie_siatki(
        siatki=siatka_PD(),
        funkcja_celu=lambda Kp, Td: cel_PD(Kp, Td, model_cls=model_cls, Kr=Kr, T=T),
    )


def strojenie_PID_grid(model_cls=Dwa_zbiorniki, T: float = 120.0):
    return przeszukiwanie_siatki(
        siatki=siatka_PID(),
        funkcja_celu=lambda Kp, Ti, Td: cel_PID(Kp, Ti, Td, model_cls=model_cls, T=T),
    )


def strojenie_P_opt(x0=(1.0,), bounds=((0.05, 20.0),), model_cls=Zbiornik_1rz, T: float = 120.0):
    f = lambda x: cel_P(float(x[0]), model_cls=model_cls, T=T)
    return optymalizacja(f, x0=[float(x0[0])], granice=list(bounds), labels=["Kp"])


def strojenie_PI_opt(x0=(1.0, 10.0), bounds=((0.05, 20.0), (1.0, 200.0)), model_cls=Zbiornik_1rz, T: float = 120.0):
    f = lambda x: cel_PI(float(x[0]), float(x[1]), model_cls=model_cls, T=T)
    return optymalizacja(f, x0=[float(x0[0]), float(x0[1])], granice=list(bounds), labels=["Kp", "Ti"])


def strojenie_PD_opt(
    x0=(1.0, 1.0),
    bounds=((0.05, 20.0), (0.0, 20.0)),
    model_cls=Dwa_zbiorniki, Kr: float = 1.0, T: float = 120.0
):
    f = lambda x: cel_PD(float(x[0]), float(x[1]), model_cls=model_cls, Kr=Kr, T=T)
    return optymalizacja(f, x0=[float(x0[0]), float(x0[1])], granice=list(bounds), labels=["Kp", "Td"])


def strojenie_PID_opt(
    x0=(1.0, 12.0, 1.0),
    bounds=((0.05, 20.0), (1.0, 200.0), (0.0, 20.0)),
    model_cls=Dwa_zbiorniki, T: float = 120.0
):
    f = lambda x: cel_PID(float(x[0]), float(x[1]), float(x[2]), model_cls=model_cls, T=T)
    return optymalizacja(
        f,
        x0=[float(x0[0]), float(x0[1]), float(x0[2])],
        granice=list(bounds),
        labels=["Kp", "Ti", "Td"],
    )


# ---------- main entry used by uruchom_symulacje.py ----------
def wykonaj_strojenie(regulator: str, metoda: str = "grid", model: str | None = None):
    """
    regulator: one of {'regulator_p','regulator_pi','regulator_pd','regulator_pid'}
    metoda: 'grid' or 'opt'
    model: override model key if needed: {'zbiornik_1rz','dwa_zbiorniki','wahadlo'}
    """
    regulator = (regulator or "").lower()

    # pick default model per regulator
    if model is None:
        if regulator in ("regulator_p", "regulator_pi"):
            model_cls = Zbiornik_1rz
        elif regulator in ("regulator_pd", "regulator_pid"):
            model_cls = Dwa_zbiorniki
        else:
            # fallback
            model_cls = Zbiornik_1rz
    else:
        key = (model or "").lower()
        model_cls = {"zbiornik_1rz": Zbiornik_1rz, "dwa_zbiorniki": Dwa_zbiorniki, "wahadlo": Wahadlo_odwrocone}.get(
            key, Zbiornik_1rz
        )

    if regulator == "regulator_p":
        if metoda == "grid":
            return strojenie_P_grid(model_cls=model_cls, T=120.0)
        else:
            return strojenie_P_opt(model_cls=model_cls, T=120.0)

    if regulator == "regulator_pi":
        if metoda == "grid":
            return strojenie_PI_grid(model_cls=model_cls, T=120.0)
        else:
            return strojenie_PI_opt(model_cls=model_cls, T=120.0)

    if regulator == "regulator_pd":
        if metoda == "grid":
            # Kr=1.0 for current models (K=1). If your model DC gain changes, set Kr≈1/K.
            return strojenie_PD_grid(model_cls=model_cls, Kr=1.0, T=120.0)
        else:
            return strojenie_PD_opt(model_cls=model_cls, Kr=1.0, T=120.0)

    if regulator == "regulator_pid":
        if metoda == "grid":
            return strojenie_PID_grid(model_cls=model_cls, T=120.0)
        else:
            return strojenie_PID_opt(model_cls=model_cls, T=120.0)

    # unknown regulator key: return empty stub
    return {"best": None, "results": []}


if __name__ == "__main__":
    print(wykonaj_strojenie("regulator_pi", "grid"))
