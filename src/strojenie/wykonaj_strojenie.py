# src/strojenie/wykonaj_strojenie.py
from __future__ import annotations
import os, json, math
import numpy as np
from typing import Dict, Any, List, Tuple

# Importy wewnętrzne – działają i przy uruchamianiu modułowym, i z pakietu
try:
    from .przeszukiwanie_siatki import przeszukiwanie_siatki
    from .optymalizacja_numeryczna import optymalizuj_podstawowy as optymalizacja
except ImportError:
    from src.strojenie.przeszukiwanie_siatki import przeszukiwanie_siatki
    from src.strojenie.optymalizacja_numeryczna import optymalizuj_podstawowy as optymalizacja

try:
    from .ziegler_nichols import policz_zn
except ImportError:
    from src.ziegler_nichols import policz_zn

from src.modele.zbiornik_1rz import Zbiornik_1rz
from src.modele.dwa_zbiorniki import Dwa_zbiorniki
from src.modele.wahadlo_odwrocone import Wahadlo_odwrocone

from src.regulatory.regulator_p import regulator_p as Regulator_P
from src.regulatory.regulator_pi import Regulator_PI
from src.regulatory.regulator_pd import Regulator_PD
from src.regulatory.regulator_pid import Regulator_PID

from src.metryki import oblicz_metryki


# ===== utilsy plikowe =====
def _ensure_dir(d: str) -> str:
    os.makedirs(d, exist_ok=True); return d

def _save_json(path: str, obj: Any) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)

def _write_csv(path: str, header: List[str], rows: List[List[Any]]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(",".join(header) + "\n")
        for r in rows:
            f.write(",".join(str(x) for x in r) + "\n")


# ===== symulacja i koszt =====
def _symuluj(model, regulator, T: float = 60.0, r_value: float = 1.0):
    dt = float(getattr(model, "dt", 0.05))
    N = int(np.ceil(T / dt))
    t = np.zeros(N); r = np.full(N, r_value, dtype=float)
    y = np.zeros(N); u = np.zeros(N); y[0] = float(getattr(model, "y", 0.0))

    # Early-stop, żeby strojenie było szybkie
    in_band = 0; settle_band = 0.02; settle_req = max(1, int(5.0 / dt))

    for k in range(1, N):
        uk = regulator.update(r[k - 1], y[k - 1])
        yk = model.step(uk)
        t[k] = k * dt; y[k] = yk; u[k] = uk
        if abs(y[k] - r[k]) <= settle_band * max(1.0, abs(r[k])):
            in_band += 1
            if in_band >= settle_req:
                t = t[: k + 1]; r = r[: k + 1]; y = y[: k + 1]; u = u[: k + 1]
                break
        else:
            in_band = 0

    m = oblicz_metryki(t, r, y, u, settle_band=settle_band)
    return m, (t, r, y, u)

def _J(metrics) -> float:
    # Funkcja celu: IAE + lekkie kary za wolne/duże Mp
    return metrics.IAE + 0.1 * metrics.czas_ustalania + 0.05 * max(0.0, metrics.przeregulowanie - 5.0)


# ===== definicje siatek =====
def _siatka_P():
    return {"Kp": np.linspace(0.1, 8.0, 30)}

def _siatka_PI():
    # umiarkowana gęstość – szybko i sensownie
    return {"Kp": np.linspace(0.3, 6.0, 18), "Ti": np.linspace(6.0, 30.0, 20)}

def _siatka_PD():
    return {"Kp": np.linspace(0.3, 6.0, 18), "Td": np.linspace(0.1, 6.0, 18)}

def _siatka_PID():
    return {"Kp": np.linspace(0.3, 6.0, 12), "Ti": np.linspace(6.0, 30.0, 12), "Td": np.linspace(0.2, 6.0, 12)}


# ===== pomocnicze twórcy modelu/regulatora =====
def _pick_model(model_key: str):
    return {"zbiornik_1rz": Zbiornik_1rz, "dwa_zbiorniki": Dwa_zbiorniki, "wahadlo_odwrocone": Wahadlo_odwrocone}.get(model_key, Zbiornik_1rz)

def _build_reg(regulator: str, params: Dict[str, float], dt: float):
    umin, umax = 0.0, 1.0
    if regulator == "regulator_p":
        return Regulator_P(Kp=params["Kp"], Kr=params.get("Kr", 1.0), dt=dt, umin=umin, umax=umax)
    if regulator == "regulator_pi":
        tt = params.get("Tt", max(params["Ti"]/2.0, 1.0))
        return Regulator_PI(kp=params["Kp"], ti=params["Ti"], tt=tt, dt=dt, umin=umin, umax=umax)
    if regulator == "regulator_pd":
        return Regulator_PD(kp=params["Kp"], td=params["Td"], Kr=params.get("Kr", 1.0), dt=dt, umin=umin, umax=umax)
    tt = params.get("Tt", max(params["Ti"]/2.0, 1.0))
    return Regulator_PID(kp=params["Kp"], ti=params["Ti"], td=params["Td"], tt=tt, beta=params.get("beta", 0.9),
                         dt=dt, umin=umin, umax=umax)


# ===== pojedyncze METODY strojenia =====
def _strojenie_grid(regulator: str, model_key: str, outdir: str, T: float = 60.0) -> Dict[str, Any]:
    model_cls = _pick_model(model_key)
    rows: List[List[float]] = []

    if regulator == "regulator_p":
        for kp in _siatka_P()["Kp"]:
            m, _ = _symuluj(model_cls(), _build_reg(regulator, {"Kp": float(kp)}, dt=model_cls().dt), T=T)
            rows.append([float(kp), float(_J(m))])
        head = ["Kp"]

    elif regulator == "regulator_pi":
        X = _siatka_PI()
        for kp in X["Kp"]:
            for ti in X["Ti"]:
                params = {"Kp": float(kp), "Ti": float(ti)}
                m, _ = _symuluj(model_cls(), _build_reg(regulator, params, dt=model_cls().dt), T=T)
                rows.append([params["Kp"], params["Ti"], float(_J(m))])
        head = ["Kp", "Ti"]

    elif regulator == "regulator_pd":
        X = _siatka_PD()
        for kp in X["Kp"]:
            for td in X["Td"]:
                params = {"Kp": float(kp), "Td": float(td)}
                m, _ = _symuluj(model_cls(), _build_reg(regulator, params, dt=model_cls().dt), T=T)
                rows.append([params["Kp"], params["Td"], float(_J(m))])
        head = ["Kp", "Td"]

    else:  # PID
        X = _siatka_PID()
        for kp in X["Kp"]:
            for ti in X["Ti"]:
                for td in X["Td"]:
                    params = {"Kp": float(kp), "Ti": float(ti), "Td": float(td)}
                    m, _ = _symuluj(model_cls(), _build_reg(regulator, params, dt=model_cls().dt), T=T)
                    rows.append([params["Kp"], params["Ti"], params["Td"], float(_J(m))])
        head = ["Kp", "Ti", "Td"]

    # zapisy
    _write_csv(os.path.join(outdir, f"siatka_{regulator}_{model_key}.csv"), head + ["J"], rows)
    top = sorted(rows, key=lambda r: r[-1])[:10]
    _save_json(os.path.join(outdir, f"top10_{regulator}_{model_key}__grid.json"),
               [{"params": dict(zip(head, r[:-1])), "J": r[-1]} for r in top])
    best = min(rows, key=lambda r: r[-1])
    return {"metoda": "grid", "best": dict(zip(head, best[:-1])), "J": best[-1]}


def _strojenie_opt(regulator: str, model_key: str, outdir: str, T: float = 60.0) -> Dict[str, Any]:
    model_cls = _pick_model(model_key)

    if regulator == "regulator_p":
        f = lambda x: _J(_symuluj(model_cls(), _build_reg(regulator, {"Kp": float(x[0])}, dt=model_cls().dt), T=T)[0])
        res = optymalizacja(f, x0=[1.0], granice=[(0.05, 20.0)], labels=["Kp"])

    elif regulator == "regulator_pi":
        f = lambda x: _J(_symuluj(model_cls(), _build_reg(regulator, {"Kp": float(x[0]), "Ti": float(x[1])}, dt=model_cls().dt), T=T)[0])
        res = optymalizacja(f, x0=[1.0, 10.0], granice=[(0.05, 20.0), (1.0, 200.0)], labels=["Kp", "Ti"])

    elif regulator == "regulator_pd":
        f = lambda x: _J(_symuluj(model_cls(), _build_reg(regulator, {"Kp": float(x[0]), "Td": float(x[1])}, dt=model_cls().dt), T=T)[0])
        res = optymalizacja(f, x0=[1.0, 1.0], granice=[(0.05, 20.0), (0.0, 20.0)], labels=["Kp", "Td"])

    else:
        f = lambda x: _J(_symuluj(model_cls(), _build_reg(regulator, {"Kp": float(x[0]), "Ti": float(x[1]), "Td": float(x[2])}, dt=model_cls().dt), T=T)[0])
        res = optymalizacja(f, x0=[1.0, 12.0, 1.0], granice=[(0.05, 20.0), (1.0, 200.0), (0.0, 20.0)], labels=["Kp", "Ti", "Td"])

    _save_json(os.path.join(outdir, f"opt_{regulator}_{model_key}.json"), res)
    return {"metoda": "opt", "best": res.get("best", {}), "J": res.get("J", None)}


def _strojenie_zn(regulator: str, model_key: str, outdir: str, T: float = 60.0) -> Dict[str, Any]:
    """
    Ziegler–Nichols: działa sensownie głównie dla PID/PI/P (nie dla PD).
    Jeśli dana para (regulator, model) nie jest wspierana przez policz_zn, zwracamy None.
    """
    try:
        params = policz_zn(regulator, model_key)
    except Exception:
        return {"metoda": "zn", "best": {}, "J": None, "uwaga": "ZN niedostępne dla tej konfiguracji"}

    if not params:
        return {"metoda": "zn", "best": {}, "J": None, "uwaga": "ZN brak wyników"}

    # oceń koszt J dla porównania
    model = _pick_model(model_key)()
    reg = _build_reg(regulator, params, dt=model.dt)
    m, _ = _symuluj(model, reg, T=T)
    return {"metoda": "zn", "best": params, "J": float(_J(m))}


# ===== API – pojedyncza metoda (dla wstecznej zgodności) =====
def wykonaj_strojenie(regulator: str, metoda: str = "grid", model: str | None = None) -> Dict[str, Any]:
    """
    Zostawiamy dla kompatybilności, ale docelowo używaj wykonaj_strojenie_multi.
    """
    return wykonaj_strojenie_multi(regulator, metody=[metoda], model=model)


# ===== API – wielometodowe strojenie na raz =====
def wykonaj_strojenie_multi(regulator: str, metody: List[str], model: str | None = None) -> Dict[str, Any]:
    regulator = (regulator or "").lower()
    model = model or ("zbiornik_1rz" if regulator in ("regulator_p", "regulator_pi") else "dwa_zbiorniki")
    outdir = _ensure_dir(os.environ.get("WYNIKI_DIR", "wyniki"))
    T = float(os.environ.get("T_TUNE", 60.0))

    wyniki: List[Dict[str, Any]] = []
    for m in metody:
        m = m.strip().lower()
        if m == "grid":
            res = _strojenie_grid(regulator, model, outdir, T=T)
        elif m in ("opt", "optim", "lbfgsb"):
            res = _strojenie_opt(regulator, model, outdir, T=T)
        elif m in ("zn", "ziegler", "ziegler-nichols"):
            res = _strojenie_zn(regulator, model, outdir, T=T)
        else:
            res = {"metoda": m, "best": {}, "J": None, "uwaga": "nieznana metoda"}
        wyniki.append(res)

        # zapisy per-metoda
        _save_json(os.path.join(outdir, f"parametry_{regulator}_{model}__{res['metoda']}.json"), res.get("best", {}))
        _save_json(os.path.join(outdir, f"rezultat_{regulator}_{model}__{res['metoda']}.json"), res)

    # wybór najlepszego (najmniejsze J z dostępnych)
    kandydaci = [w for w in wyniki if w.get("J") is not None and isinstance(w.get("best"), dict) and w["best"]]
    if kandydaci:
        best_all = min(kandydaci, key=lambda w: w["J"])
        najlepsze_param = best_all["best"]
    else:
        best_all = {"metoda": None, "J": None, "best": {}}
        najlepsze_param = {}

    # główny plik parametrów (bez sufiksu) – zwycięzca
    _save_json(os.path.join(outdir, f"parametry_{regulator}_{model}.json"), najlepsze_param)

    # ładny zbiorczy raport HTML
    def _row(w: Dict[str, Any]) -> str:
        j = "—" if w.get("J") is None else f"{w['J']:.3f}"
        uw = w.get("uwaga", "")
        return f"<tr><td>{w.get('metoda','?')}</td><td><code>{json.dumps(w.get('best', {}))}</code></td><td>{j}</td><td>{uw}</td></tr>"

    rows = "\n".join(_row(w) for w in wyniki) or "<tr><td colspan='4'>Brak wyników</td></tr>"
    html = f"""<!doctype html><html><head><meta charset="utf-8">
<title>Strojenie {regulator} / {model}</title>
<style>
body{{font-family:Inter,Segoe UI,Arial,sans-serif;margin:22px}}
table{{border-collapse:collapse;width:100%}} th,td{{border:1px solid #e3e3e3;padding:8px}} th{{background:#fafafa}}
code{{font-family:ui-monospace,Consolas,monospace}}
.badge{{display:inline-block;background:#eef;border:1px solid #ccd;padding:4px 8px;border-radius:6px}}
</style></head><body>
<h2>Strojenie <span class="badge">{regulator}</span> / <span class="badge">{model}</span></h2>
<p><b>Metody:</b> {", ".join(metody)}</p>
<table><thead><tr><th>Metoda</th><th>Parametry</th><th>J</th><th>Uwaga</th></tr></thead><tbody>
{rows}
</tbody></table>
<p><b>Najlepsze (J min):</b> metoda = <code>{best_all.get('metoda')}</code>,
 parametry = <code>{json.dumps(najlepsze_param)}</code></p>
</body></html>"""
    with open(os.path.join(outdir, f"raport_strojenie_{regulator}_{model}.html"), "w", encoding="utf-8") as f:
        f.write(html)

    return {"wyniki": wyniki, "best_all": best_all}
