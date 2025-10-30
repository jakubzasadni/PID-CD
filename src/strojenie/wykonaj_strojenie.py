# src/wykonaj_strojenie.py
from __future__ import annotations
import numpy as np

from src.modele.zbiornik_1rz import Zbiornik_1rz
from src.modele.dwa_zbiorniki import Dwa_zbiorniki
from src.modele.wahadlo_odwrocone import Wahadlo_odwrocone

from src.regulatory.regulator_pi import Regulator_PI
from src.regulatory.regulator_pid import Regulator_PID
from src.regulatory.regulator_pd import Regulator_PD

from src.metryki import oblicz_metryki
from src.przeszukiwanie_siatki import przeszukiwanie_siatki
from src.optymalizacja_numeryczna import optymalizacja


# ---------- simulation helper ----------
def symuluj(model, regulator, T: float = 120.0, r_value: float = 1.0):
    dt = float(model.dt)
    N = int(np.ceil(T / dt))
    t = np.zeros(N)
    r = np.full(N, r_value, dtype=float)
    y = np.zeros(N)
    u = np.zeros(N)

    # initial output
    y[0] = float(getattr(model, "y", 0.0))

    for k in range(1, N):
        uk = regulator.update(r[k - 1], y[k - 1])
        yk = model.step(uk)
        t[k] = k * dt
        y[k] = yk
        u[k] = uk

    m = oblicz_metryki(t, r, y, u, settle_band=0.02)
    return m, (t, r, y, u)


# ---------- objective functions ----------
def cel_PI(Kp: float, Ti: float, model_cls=Zbiornik_1rz, T: float = 120.0) -> float:
    model = model_cls()
    reg = Regulator_PI(kp=Kp, ti=Ti, tt=max(Ti / 2.0, 1.0), dt=model.dt, umin=0.0, umax=1.0)
    m, _ = symuluj(model, reg, T=T, r_value=1.0)
    # IAE + mild penalties for long ts and large overshoot
    return m.IAE + 0.1 * m.czas_ustalania + 0.05 * max(0.0, m.przeregulowanie - 5.0)


def cel_PID(Kp: float, Ti: float, Td: float, model_cls=Dwa_zbiorniki, T: float = 120.0) -> float:
    model = model_cls()
    reg = Regulator_PID(
        kp=Kp, ti=Ti, td=Td, tt=max(Ti / 2.0, 1.0),
        beta=0.9, dt=model.dt, umin=0.0, umax=1.0
    )
    m, _ = symuluj(model, reg, T=T, r_value=1.0)
    return m.IAE + 0.1 * m.czas_ustalania + 0.05 * max(0.0, m.przeregulowanie - 5.0)


def cel_PD(Kp: float, Td: float, model_cls=Dwa_zbiorniki, Kr: float = 1.0, T: float = 120.0) -> float:
    model = model_cls()
    reg = Regulator_PD(kp=Kp, td=Td, Kr=Kr, dt=model.dt, umin=0.0, umax=1.0)
    m, _ = symuluj(model, reg, T=T, r_value=1.0)
    return m.IAE + 0.1 * m.czas_ustalania + 0.05 * max(0.0, m.przeregulowanie - 5.0)


# ---------- grid search presets ----------
def siatka_PI():
    return {
        "Kp": np.linspace(0.5, 6.0, 30),
        "Ti": np.linspace(4.0, 30.0, 40),
    }


def siatka_PID():
    return {
        "Kp": np.linspace(0.5, 6.0, 26),
        "Ti": np.linspace(6.0, 30.0, 25),
        "Td": np.linspace(0.2, 6.0, 25),
    }


def siatka_PD():
    return {
        "Kp": np.linspace(0.5, 6.0, 30),
        "Td": np.linspace(0.1, 6.0, 30),
    }


# ---------- public API ----------
def strojenie_PI_grid(model_cls=Zbiornik_1rz, T: float = 120.0):
    return przeszukiwanie_siatki(
        siatki=siatka_PI(),
        funkcja_celu=lambda Kp, Ti: cel_PI(Kp, Ti, model_cls=model_cls, T=T),
    )


def strojenie_PID_grid(model_cls=Dwa_zbiorniki, T: float = 120.0):
    return przeszukiwanie_siatki(
        siatki=siatka_PID(),
        funkcja_celu=lambda Kp, Ti, Td: cel_PID(Kp, Ti, Td, model_cls=model_cls, T=T),
    )


def strojenie_PD_grid(model_cls=Dwa_zbiorniki, Kr: float = 1.0, T: float = 120.0):
    return przeszukiwanie_siatki(
        siatki=siatka_PD(),
        funkcja_celu=lambda Kp, Td: cel_PD(Kp, Td, model_cls=model_cls, Kr=Kr, T=T),
    )


def strojenie_PI_opt(x0=(1.0, 10.0), bounds=((0.05, 20.0), (1.0, 200.0)), model_cls=Zbiornik_1rz, T: float = 120.0):
    f = lambda x: cel_PI(float(x[0]), float(x[1]), model_cls=model_cls, T=T)
    return optymalizacja(f, x0=np.array(x0, dtype=float), bounds=np.array(bounds, dtype=float), method="L-BFGS-B")


def strojenie_PID_opt(
    x0=(1.0, 12.0, 1.0),
    bounds=((0.05, 20.0), (1.0, 200.0), (0.0, 20.0)),
    model_cls=Dwa_zbiorniki, T: float = 120.0
):
    f = lambda x: cel_PID(float(x[0]), float(x[1]), float(x[2]), model_cls=model_cls, T=T)
    return optymalizacja(f, x0=np.array(x0, dtype=float), bounds=np.array(bounds, dtype=float), method="L-BFGS-B")


def strojenie_PD_opt(
    x0=(1.0, 1.0),
    bounds=((0.05, 20.0), (0.0, 20.0)),
    model_cls=Dwa_zbiorniki, Kr: float = 1.0, T: float = 120.0
):
    f = lambda x: cel_PD(float(x[0]), float(x[1]), model_cls=model_cls, Kr=Kr, T=T)
    return optymalizacja(f, x0=np.array(x0, dtype=float), bounds=np.array(bounds, dtype=float), method="L-BFGS-B")


# ---------- example usage ----------
if __name__ == "__main__":
    # PI on 1st-order tank
    best_pi = strojenie_PI_grid(model_cls=Zbiornik_1rz, T=120.0)
    print("PI grid best:", best_pi.get("best"))

    # PID on two-tank system
    best_pid = strojenie_PID_grid(model_cls=Dwa_zbiorniki, T=120.0)
    print("PID grid best:", best_pid.get("best"))

    # PD with feed-forward Kr=1 (K=1 for current models)
    best_pd = strojenie_PD_grid(model_cls=Dwa_zbiorniki, Kr=1.0, T=120.0)
    print("PD grid best:", best_pd.get("best"))
