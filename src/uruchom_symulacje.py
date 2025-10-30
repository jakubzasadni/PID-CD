# src/uruchom_symulacje.py
from __future__ import annotations
import os, json, time, glob
from typing import Dict, Any, Tuple

from src.strojenie.wykonaj_strojenie import wykonaj_strojenie_multi
from src.metryki import oblicz_metryki

from src.modele.zbiornik_1rz import Zbiornik_1rz
from src.modele.dwa_zbiorniki import Dwa_zbiorniki
from src.modele.wahadlo_odwrocone import Wahadlo_odwrocone

from src.regulatory.regulator_p import regulator_p as RegP
from src.regulatory.regulator_pi import Regulator_PI as RegPI
from src.regulatory.regulator_pd import Regulator_PD as RegPD
from src.regulatory.regulator_pid import Regulator_PID as RegPID

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def _stamp(): return time.strftime("%Y%m%d-%H%M%S")
def _outdir():
    d = os.environ.get("WYNIKI_DIR", "wyniki"); os.makedirs(d, exist_ok=True); return d

def _pick_model(key: str, dt_env: str | None):
    dt = float(dt_env) if dt_env else None
    if key == "zbiornik_1rz":
        m = Zbiornik_1rz()
    elif key == "dwa_zbiorniki":
        m = Dwa_zbiorniki()
    else:
        m = Wahadlo_odwrocone(dt=float(dt) if dt else 0.05)
    if dt and hasattr(m, "dt"):
        m.dt = float(dt)
    return m

def _make_reg(reg: str, params: Dict[str, float], dt: float):
    umin, umax = 0.0, 1.0
    if reg == "regulator_p":
        return RegP(Kp=params.get("Kp", 1.0), Kr=params.get("Kr", 1.0), dt=dt, umin=umin, umax=umax)
    if reg == "regulator_pi":
        kp = params.get("Kp", 1.0); ti = params.get("Ti", 10.0); tt = params.get("Tt", max(ti/2,1.0))
        return RegPI(kp=kp, ti=ti, tt=tt, dt=dt, umin=umin, umax=umax)
    if reg == "regulator_pd":
        kp = params.get("Kp", 1.0); td = params.get("Td", 1.0)
        return RegPD(kp=kp, td=td, Kr=params.get("Kr", 1.0), dt=dt, umin=umin, umax=umax)
    kp = params.get("Kp", 1.0); ti = params.get("Ti", 10.0); td = params.get("Td", 1.0)
    tt = params.get("Tt", max(ti/2,1.0))
    return RegPID(kp=kp, ti=ti, td=td, tt=tt, beta=params.get("beta", 0.9), dt=dt, umin=umin, umax=umax)

def _simulate(model, regulator, T: float = 60.0, r_value: float = 1.0):
    dt = float(getattr(model, "dt", 0.05))
    N = int(T / dt)
    t = [0.0]; r = [r_value]; y = [float(getattr(model, "y", 0.0))]; u = [0.0]
    for k in range(1, N):
        uk = regulator.update(r[-1], y[-1]); yk = model.step(uk)
        t.append(k*dt); r.append(r_value); y.append(yk); u.append(uk)
    return oblicz_metryki(t, r, y, u), (t, r, y, u)

def _plot(path_noext: str, title: str, t, r, y, u, m) -> None:
    c_ref = "#7f8c8d"; c_y = "#2c7be5"; c_u = "#d74e09"
    fig = plt.figure(figsize=(11, 8))
    gs = fig.add_gridspec(2, 1, height_ratios=[2, 1], hspace=0.25)
    ax1 = fig.add_subplot(gs[0]); ax2 = fig.add_subplot(gs[1])

    ax1.plot(t, r, linestyle=(0,(6,3)), color=c_ref, linewidth=2, label="r")
    ax1.plot(t, y, color=c_y, linewidth=2.5, label="y")
    ax1.set_title(title, pad=8); ax1.set_xlabel("t [s]"); ax1.set_ylabel("Wartość"); ax1.grid(True, alpha=0.25)
    ax1.legend(loc="upper right", frameon=True, framealpha=0.9)

    ax2.plot(t, u, color=c_u, linewidth=2.2, label="u")
    ax2.set_xlabel("t [s]"); ax2.set_ylabel("Sterowanie"); ax2.grid(True, alpha=0.25)
    ax2.legend(loc="upper right", frameon=True, framealpha=0.9)

    txt = f"IAE: {m.IAE:.2f}\nMp: {m.przeregulowanie:.1f}%\nts: {m.czas_ustalania:.1f}s\ntr: {m.czas_narastania:.1f}s\nEu: {m.uchyb_ustalony:.3g}"
    ax1.annotate(txt, xy=(0.01, 0.02), xycoords="axes fraction",
                 bbox=dict(boxstyle="round,pad=0.35", fc="white", ec="#d0d0d0"))

    y_all = list(y) + list(r); pad = 0.06 * (max(y_all) - min(y_all) + 1e-9)
    ax1.set_ylim(min(y_all) - pad, max(y_all) + pad)

    fig.tight_layout()
    fig.savefig(path_noext + ".png", dpi=140)
    fig.savefig(path_noext + ".svg")
    plt.close(fig)


def _find_params(dirpath: str, reg: str, model: str) -> Dict[str, Any] | None:
    cand = glob.glob(os.path.join(dirpath, f"parametry_{reg}_{model}.json"))
    if not cand:
        cand = sorted(glob.glob(os.path.join(dirpath, f"parametry_{reg}_{model}_*.json")))
    if not cand: return None
    with open(cand[-1], "r") as f:
        try:
            data = json.load(f)
        except Exception:
            return None
    if isinstance(data, dict) and "best" in data and isinstance(data["best"], dict):
        return data["best"]
    return data if isinstance(data, dict) else None


# ===== tryby =====
def run_tune(reg: str, model: str):
    # lista metod z ENV (np. "grid,opt,zn"); domyślnie wszystkie 3
    metody_env = os.environ.get("METODY_STROJENIA", "grid,opt,zn")
    metody = [m.strip() for m in metody_env.split(",") if m.strip()]
    _ = wykonaj_strojenie_multi(reg, metody=metody, model=model)
    # wszystkie artefakty (per-metoda + zwycięzca) zapisuje funkcja wyżej

def run_validate(reg: str, model_key: str, dt_env: str | None):
    out = _outdir()
    params = _find_params(out, reg, model_key) or {}
    model = _pick_model(model_key, dt_env)
    regulator = _make_reg(reg, params, getattr(model, "dt", 0.05))

    metryki, (t, r, y, u) = _simulate(model, regulator, T=60.0, r_value=1.0)
    PASS = (metryki.przeregulowanie <= 10.0) and (metryki.czas_ustalania <= 0.6 * 60.0)

    base = os.path.join(out, f"run_{reg}_{model_key}_{_stamp()}")
    _plot(base, f"{reg} — {model_key}", t, r, y, u, metryki)

    wal = {
        "regulator": reg, "model": model_key, "parametry": params,
        "metryki": {
            "IAE": metryki.IAE, "ISE": metryki.ISE, "ITAE": metryki.ITAE,
            "Mp": metryki.przeregulowanie, "ts": metryki.czas_ustalania,
            "tr": metryki.czas_narastania, "Eu": metryki.uchyb_ustalony,
            "sat_pct": metryki.procent_czasu_w_saturacji,
        },
        "PASS": bool(PASS),
        "plot_png": os.path.basename(base) + ".png",
        "plot_svg": os.path.basename(base) + ".svg",
    }
    with open(os.path.join(out, f"walidacja_{reg}_{model_key}.json"), "w") as f:
        json.dump(wal, f, indent=2)

    raport = {
        "key": f"{reg}:{model_key}", "regulator": reg, "model": model_key,
        "emoji": "✅" if PASS else "❌",
        "summary": f"{reg} on {model_key}",
        "metrics": {"Mp": metryki.przeregulowanie, "ts": metryki.czas_ustalania, "IAE": metryki.IAE},
        "plot": wal["plot_png"],
    }
    with open(os.path.join(out, f"raport_{reg}_{model_key}.json"), "w") as f:
        json.dump(raport, f, indent=2)

    if PASS:
        with open(os.path.join(out, "passed_models.txt"), "a") as f:
            f.write(f"{model_key}\n")


if __name__ == "__main__":
    REG = os.environ.get("REGU
