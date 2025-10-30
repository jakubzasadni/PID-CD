# src/uruchom_symulacje.py
from __future__ import annotations
import os, json, time, glob
from typing import Tuple, Dict, Any

# --- importy projektu ---
from src.strojenie.wykonaj_strojenie import wykonaj_strojenie
from src.metryki import oblicz_metryki

from src.modele.zbiornik_1rz import Zbiornik_1rz
from src.modele.dwa_zbiorniki import Dwa_zbiorniki
from src.modele.wahadlo_odwrocone import Wahadlo_odwrocone

from src.regulatory.regulator_p import regulator_p as RegP
from src.regulatory.regulator_pi import Regulator_PI as RegPI
from src.regulatory.regulator_pd import Regulator_PD as RegPD
from src.regulatory.regulator_pid import Regulator_PID as RegPID


# ---------- helpers ----------
def now_stamp() -> str:
    return time.strftime("%Y%m%d-%H%M%S")

def wyniki_dir() -> str:
    d = os.environ.get("WYNIKI_DIR", "wyniki")
    os.makedirs(d, exist_ok=True)
    return d

def pick_model(model_key: str, dt_env: str | None) -> Any:
    dt = float(dt_env) if dt_env else None
    if model_key == "zbiornik_1rz":
        m = Zbiornik_1rz()
    elif model_key == "dwa_zbiorniki":
        m = Dwa_zbiorniki()
    else:
        m = Wahadlo_odwrocone(dt=float(dt) if dt else 0.05)
    if dt and hasattr(m, "dt"):
        m.dt = float(dt)
    return m

def make_reg(reg_key: str, params: Dict[str, float], model_dt: float) -> Any:
    # domyślne ograniczenia sterowania
    umin, umax = 0.0, 1.0

    if reg_key == "regulator_p":
        Kp = params.get("Kp") or params.get("kp") or params.get("KP") or 1.0
        Kr = params.get("Kr", 1.0)
        return RegP(Kp=Kp, Kr=Kr, dt=model_dt, umin=umin, umax=umax)

    if reg_key == "regulator_pi":
        kp = params.get("Kp", params.get("kp", 1.0))
        ti = params.get("Ti", params.get("ti", 10.0))
        tt = params.get("Tt", params.get("tt", max(ti/2, 1.0)))
        return RegPI(kp=kp, ti=ti, tt=tt, dt=model_dt, umin=umin, umax=umax)

    if reg_key == "regulator_pd":
        kp = params.get("Kp", params.get("kp", 1.0))
        td = params.get("Td", params.get("td", 1.0))
        Kr = params.get("Kr", 1.0)  # dla Twoich modeli K≈1 → Kr=1
        return RegPD(kp=kp, td=td, Kr=Kr, dt=model_dt, umin=umin, umax=umax)

    # PID
    kp = params.get("Kp", params.get("kp", 1.0))
    ti = params.get("Ti", params.get("ti", 10.0))
    td = params.get("Td", params.get("td", 1.0))
    tt = params.get("Tt", params.get("tt", max(ti/2, 1.0)))
    beta = params.get("beta", 0.9)
    return RegPID(kp=kp, ti=ti, td=td, tt=tt, beta=beta, dt=model_dt, umin=umin, umax=umax)

def simulate(model, regulator, T: float = 120.0, r_value: float = 1.0):
    dt = float(getattr(model, "dt", 0.05))
    N = int(T / dt)
    t = [0.0]
    r = [r_value]
    y = [float(getattr(model, "y", 0.0))]
    u = [0.0]
    for k in range(1, N):
        uk = regulator.update(r[-1], y[-1])
        yk = model.step(uk)
        t.append(k*dt); r.append(r_value); y.append(yk); u.append(uk)
    return oblicz_metryki(t, r, y, u), (t, r, y, u)

def find_latest_params(dirpath: str, reg: str, model: str) -> Dict[str, Any] | None:
    pat = os.path.join(dirpath, f"parametry_{reg}_{model}_*.json")
    files = sorted(glob.glob(pat))
    if not files:
        return None
    with open(files[-1], "r") as f:
        try:
            data = json.load(f)
        except Exception:
            return None
    if isinstance(data, dict) and "best" in data and isinstance(data["best"], dict):
        return data["best"]
    return data if isinstance(data, dict) else None


# ---------- main modes ----------
def run_tune(reg: str, model: str):
    out = wykonaj_strojenie(reg, metoda="grid", model=model) or {}
    best = out.get("best") or {}
    stamp = now_stamp()
    outdir = wyniki_dir()

    # zapisz parametry
    with open(os.path.join(outdir, f"parametry_{reg}_{model}_{stamp}.json"), "w") as f:
        json.dump(best, f, indent=2)

    # prosty raport HTML
    with open(os.path.join(outdir, f"raport_strojenie_{reg}_{model}_{stamp}.html"), "w") as f:
        f.write(f"<html><body><h1>Strojenie {reg} / {model}</h1><pre>{json.dumps(best, indent=2)}</pre></body></html>")

    # pieczatka png (pusty plik – zeby artifact zawsze mial cos graficznego)
    open(os.path.join(outdir, f"strojenie_{reg}_{model}_{stamp}.png"), "wb").close()

def run_validate(reg: str, model_key: str, dt_env: str | None):
    outdir = wyniki_dir()
    params = find_latest_params(outdir, reg, model_key) or {}
    model = pick_model(model_key, dt_env)
    regulator = make_reg(reg, params, getattr(model, "dt", 0.05))

    metryki, _ = simulate(model, regulator, T=120.0, r_value=1.0)

    # progi (przyklad – dopasuj do swoich wymagan)
    pass_cond = (metryki.przeregulowanie <= 10.0) and (metryki.czas_ustalania <= 0.6 * 120.0)

    stamp = now_stamp()
    wal_json = {
        "regulator": reg,
        "model": model_key,
        "parametry": params,
        "metryki": {
            "IAE": metryki.IAE,
            "ISE": metryki.ISE,
            "ITAE": metryki.ITAE,
            "Mp": metryki.przeregulowanie,
            "ts": metryki.czas_ustalania,
            "tr": metryki.czas_narastania,
            "Eu": metryki.uchyb_ustalony,
            "sat_pct": metryki.procent_czasu_w_saturacji,
        },
        "PASS": bool(pass_cond),
    }
    with open(os.path.join(outdir, f"walidacja_{reg}_{model_key}_{stamp}.json"), "w") as f:
        json.dump(wal_json, f, indent=2)

    # raport_*.json – to konsumuje ocena_metod/summary
    raport = {
        "key": f"{reg}:{model_key}",
        "emoji": "✅" if pass_cond else "❌",
        "summary": f"{reg} on {model_key}",
        "metrics": {"Mp": metryki.przeregulowanie, "ts": metryki.czas_ustalania, "IAE": metryki.IAE},
    }
    with open(os.path.join(outdir, f"raport_{reg}_{model_key}_{stamp}.json"), "w") as f:
        json.dump(raport, f, indent=2)

    # jesli PASS – dopisz do listy wdrozen
    if pass_cond:
        with open(os.path.join(outdir, "passed_models.txt"), "a") as f:
            f.write(f"{model_key}\n")


if __name__ == "__main__":
    REG = os.environ.get("REGULATOR", "regulator_pid")
    TRYB = os.environ.get("TRYB", "strojenie")
    MODEL = os.environ.get("MODEL", None) or (
        "zbiornik_1rz" if REG in ("regulator_p", "regulator_pi") else "dwa_zbiorniki"
    )
    DT = os.environ.get("DT")  # np. dla wahadla

    if TRYB == "walidacja":
        run_validate(REG, MODEL, DT)
    else:
        run_tune(REG, MODEL)
