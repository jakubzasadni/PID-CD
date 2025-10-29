# src/strojenie/wykonaj_strojenie.py
"""
Wywołanie metod strojenia regulatorów + zapis JSON/HTML.
Obsługa: regulator_p, regulator_pi, regulator_pd, regulator_pid.
"""

import os
import json
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime

from src.strojenie.ziegler_nichols import strojenie_PID
from src.strojenie.przeszukiwanie_siatki import przeszukiwanie_siatki
from src.strojenie.optymalizacja_numeryczna import optymalizuj_podstawowy

# ---------------- helpers ----------------
def _get(d, keys, default=None):
    for k in keys:
        if k in d and d[k] is not None:
            return d[k]
    return default

def _round_or_none(x, nd=2):
    if x is None: return None
    try: return round(float(x), nd)
    except: return None

def _filter_for_regulator(reg, params):
    reg = reg.lower()
    kp = _get(params, ["Kp","kp"], 1.0)
    ti = _get(params, ["Ti","ti"], None)
    td = _get(params, ["Td","td"], None)

    if reg == "regulator_p":
        return {"Kp": _round_or_none(kp), "Ti": None, "Td": None}
    if reg == "regulator_pi":
        return {"Kp": _round_or_none(kp), "Ti": _round_or_none(ti), "Td": None}
    if reg == "regulator_pd":
        return {"Kp": _round_or_none(kp), "Ti": None, "Td": _round_or_none(td)}
    # PID
    return {"Kp": _round_or_none(kp), "Ti": _round_or_none(ti), "Td": _round_or_none(td)}

def _zapisz_raport_html(meta, parametry, historia=None, out_dir="wyniki"):
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"raport_strojenie_{meta['regulator']}_{meta['metoda']}.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write("<html><head><meta charset='utf-8'>")
        f.write(f"<title>Raport strojenia – {meta['regulator']} / {meta['metoda']}</title>")
        f.write("<style>body{font-family:Arial;margin:20px}table{border-collapse:collapse}"
                "td,th{border:1px solid #aaa;padding:6px}th{background:#eee}</style></head><body>")
        f.write(f"<h2>📘 Raport strojenia – {meta['regulator']} / {meta['metoda']}</h2>")
        f.write(f"<p>Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>")
        f.write("<table><tr><th>Parametr</th><th>Wartość</th></tr>")
        for k in ["Kp","Ti","Td"]:
            v = parametry.get(k)
            f.write(f"<tr><td>{k}</td><td>{'-' if v is None else v}</td></tr>")
        f.write("</table>")
        if historia and len(historia) > 1:
            plt.figure()
            plt.plot(historia)
            plt.xlabel("Iteracja"); plt.ylabel("Funkcja celu")
            plt.title(f"Postęp optymalizacji – {meta['metoda']}")
            fn = f"strojenie_{meta['regulator']}_{meta['metoda']}.png"
            plt.savefig(os.path.join(out_dir, fn), dpi=120); plt.close()
            f.write(f"<p><img src='{fn}' width='640'></p>")
        f.write("</body></html>")
    print(f"✅ Zapisano raport HTML: {path}")
    return path

# ---------------- main ----------------
def wykonaj_strojenie(metoda="ziegler_nichols"):
    out_dir = "wyniki"
    os.makedirs(out_dir, exist_ok=True)

    regulator = os.getenv("REGULATOR", "regulator_pid").lower()
    historia = []

    # 1) Parametry pełne Kp, Ti, Td (później przytniemy do typu)
    if metoda == "ziegler_nichols":
        pelne = strojenie_PID(Ku=2.0, Tu=25.0)  # baza; niżej przytniemy wg typu

    elif metoda == "siatka":
        if regulator == "regulator_p":
            pelne = przeszukiwanie_siatki(
                siatki={"Kp": np.linspace(0.5, 6.0, 30)},
                funkcja_celu=lambda Kp: (Kp - 3.0) ** 2  # niech P będzie żwawsze
            )
        elif regulator == "regulator_pi":
            pelne = przeszukiwanie_siatki(
                siatki={
                    "Kp": np.linspace(1.0, 6.0, 26),
                    "Ti": np.linspace(8.0, 22.0, 29),   # szybsza całka
                },
                funkcja_celu=lambda Kp, Ti: (Kp - 3.0) ** 2 + 0.5 * (Ti - 14.0) ** 2
            )
        elif regulator == "regulator_pd":
            pelne = przeszukiwanie_siatki(
                siatki={
                    "Kp": np.linspace(1.0, 6.0, 26),
                    "Td": np.linspace(0.5, 5.0, 19),
                },
                funkcja_celu=lambda Kp, Td: (Kp - 3.0) ** 2 + (Td - 3.0) ** 2
            )
        else:  # PID
            pelne = przeszukiwanie_siatki(
                siatki={
                    "Kp": np.linspace(1.0, 6.0, 26),
                    "Ti": np.linspace(8.0, 22.0, 29),
                    "Td": np.linspace(0.5, 5.0, 19),
                },
                funkcja_celu=lambda Kp, Ti, Td: (Kp - 3.0) ** 2 + 0.5 * (Ti - 14.0) ** 2 + (Td - 3.0) ** 2
            )

    elif metoda == "optymalizacja":
        # prosty, szybki cel (bez wołania symulacji) – przesunięty na szybsze czasy
        if regulator == "regulator_p":
            def f(x): v = (x[0] - 3.0) ** 2; historia.append(v); return v
            wynik = optymalizuj_podstawowy(f, x0=[2.0], granice=[(0.2, 8.0)])
            pelne = {"Kp": wynik.get("Kp", 3.0), "Ti": None, "Td": None}

        elif regulator == "regulator_pi":
            def f(x): v = (x[0] - 3.0) ** 2 + 0.5 * (x[1] - 14.0) ** 2; historia.append(v); return v
            wynik = optymalizuj_podstawowy(f, x0=[2.0, 12.0], granice=[(0.5, 8.0), (6.0, 30.0)])
            pelne = {"Kp": wynik.get("Kp", 3.0), "Ti": wynik.get("Ti", 14.0), "Td": None}

        elif regulator == "regulator_pd":
            def f(x): v = (x[0] - 3.0) ** 2 + (x[1] - 3.0) ** 2; historia.append(v); return v
            wynik = optymalizuj_podstawowy(f, x0=[2.0, 2.0], granice=[(0.5, 8.0), (0.5, 5.0)])
            pelne = {"Kp": wynik.get("Kp", 3.0), "Ti": None, "Td": wynik.get("Td", 3.0)}

        else:  # PID
            def f(x): v = (x[0] - 3.0) ** 2 + 0.5 * (x[1] - 14.0) ** 2 + (x[2] - 3.0) ** 2; historia.append(v); return v
            wynik = optymalizuj_podstawowy(
                f, x0=[2.0, 12.0, 2.0],
                granice=[(0.5, 8.0), (6.0, 30.0), (0.5, 5.0)]
            )
            pelne = {"Kp": wynik.get("Kp", 3.0), "Ti": wynik.get("Ti", 14.0), "Td": wynik.get("Td", 3.0)}

    else:
        raise ValueError(f"❌ Nieznana metoda strojenia: {metoda}")

    # 2) Przytnij do typu
    params = _filter_for_regulator(regulator, pelne)

    # 3) Zapisz JSON + HTML
    meta = {"regulator": regulator, "metoda": metoda}
    out = {"regulator": regulator, "metoda": metoda, "parametry": params}
    json_path = os.path.join(out_dir, f"parametry_{regulator}_{metoda}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(f"💾 Zapisano parametry: {json_path}")

    _zapisz_raport_html(meta, params, historia, out_dir)
    return params

if __name__ == "__main__":
    for m in ["ziegler_nichols", "siatka", "optymalizacja"]:
        wykonaj_strojenie(m)
