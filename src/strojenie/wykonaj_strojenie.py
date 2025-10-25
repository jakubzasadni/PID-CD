"""
Moduł wywołujący różne metody strojenia regulatorów.
Zwraca zestaw parametrów do testów walidacyjnych i generuje raport HTML.
Obsługiwane regulatory: regulator_p, regulator_pi, regulator_pd, regulator_pid.
"""

import os
import json
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime

from src.strojenie.ziegler_nichols import strojenie_PID
from src.strojenie.przeszukiwanie_siatki import przeszukiwanie_siatki
from src.strojenie.optymalizacja_numeryczna import optymalizuj_podstawowy


def _fmt(v):
    try:
        return round(float(v), 2)
    except Exception:
        return "-"


def _filter_for_regulator(reg_name: str, params: dict) -> dict:
    """Przytnij słownik parametrów do tych, które mają sens dla danego typu regulatora."""
    reg = reg_name.lower()
    kp = params.get("Kp") or params.get("kp") or params.get("k") or params.get("p")
    ti = params.get("Ti") or params.get("ti") or params.get("i") or params.get("taui")
    td = params.get("Td") or params.get("td") or params.get("d") or params.get("taud")

    if reg == "regulator_p":
        return {"Kp": _fmt(kp)}
    if reg == "regulator_pi":
        return {"Kp": _fmt(kp), "Ti": _fmt(ti)}
    if reg == "regulator_pd":
        return {"Kp": _fmt(kp), "Td": _fmt(td)}
    return {"Kp": _fmt(kp), "Ti": _fmt(ti), "Td": _fmt(td)}


def _zapisz_raport_html(meta, parametry, historia=None, out_dir="wyniki"):
    os.makedirs(out_dir, exist_ok=True)
    html_path = os.path.join(out_dir, f"raport_strojenie_{meta['regulator']}_{meta['metoda']}.html")

    with open(html_path, "w", encoding="utf-8") as f:
        f.write("<html><head><meta charset='utf-8'>")
        f.write(f"<title>Raport strojenia – {meta['regulator']} / {meta['metoda']}</title>")
        f.write("<style>body{font-family:Arial,sans-serif;margin:20px;} "
                "table{border-collapse:collapse;} td,th{border:1px solid #aaa;padding:6px;} "
                "th{background:#ddd;} h2{color:#333;}</style></head><body>")
        f.write(f"<h2>📘 Raport strojenia – {meta['regulator']} / {meta['metoda']}</h2>")
        f.write(f"<p>Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>")

        f.write("<table><tr><th>Parametr</th><th>Wartość</th></tr>")
        for k in ["Kp", "Ti", "Td"]:
            if k in parametry:
                f.write(f"<tr><td>{k}</td><td>{parametry[k]}</td></tr>")
        f.write("</table>")

        if historia and len(historia) > 1:
            plt.figure()
            plt.plot(historia)
            plt.xlabel("Iteracja")
            plt.ylabel("Funkcja celu")
            plt.title(f"Postęp optymalizacji – {meta['metoda']}")
            wykres_path = os.path.join(out_dir, f"strojenie_{meta['regulator']}_{meta['metoda']}.png")
            plt.savefig(wykres_path, dpi=120)
            plt.close()
            f.write(f"<p><img src='strojenie_{meta['regulator']}_{meta['metoda']}.png' width='600'></p>")

        f.write("</body></html>")

    print(f"✅ Zapisano raport HTML: {html_path}")
    return html_path


def wykonaj_strojenie(metoda="ziegler_nichols"):
    """
    Uruchamia proces strojenia zgodnie z wybraną metodą.
    Metoda zwraca parametry już przycięte do aktualnego typu REGULATOR (env).
    Wynik zapisuje jako: wyniki/parametry_{REGULATOR}_{metoda}.json
    """
    out_dir = "wyniki"
    os.makedirs(out_dir, exist_ok=True)

    regulator = os.getenv("REGULATOR", "regulator_pid")  # np. regulator_p / regulator_pd / regulator_pi / regulator_pid
    historia = None

    # --- 1) wyznacz parametry "pełne" (Kp,Ti,Td) ---
    if metoda == "ziegler_nichols":
        pelne = strojenie_PID(Ku=2.0, Tu=25.0)

    elif metoda == "siatka":
        pelne = przeszukiwanie_siatki(
            siatki={
                "Kp": np.linspace(0.5, 5.0, 10),
                "Ti": np.linspace(5, 60, 10),
                "Td": np.linspace(0.0, 10.0, 6)
            },
            funkcja_celu=lambda Kp, Ti, Td: (Kp - 2) ** 2 + (Ti - 30) ** 2 + (Td - 0) ** 2
        )

    elif metoda == "optymalizacja":
        historia = []

        def f(x):
            wartosc = (x[0] - 2) ** 2 + (x[1] - 30) ** 2 + (x[2] - 0) ** 2
            historia.append(wartosc)
            return wartosc

        wynik = optymalizuj_podstawowy(
            f,
            x0=[1.0, 20.0, 0.0],
            granice=[(0.1, 10), (5, 100), (0.0, 10.0)]
        )

        # ✅ fix: obsługa słownika zamiast listy
        if isinstance(wynik, dict):
            pelne = {"Kp": wynik.get("Kp", 1.0), "Ti": wynik.get("Ti", 30.0), "Td": wynik.get("Td", 0.0)}
        else:
            pelne = {"Kp": wynik[0], "Ti": wynik[1], "Td": wynik[2]}

    else:
        raise ValueError(f"❌ Nieznana metoda strojenia: {metoda}")

    # --- 2) przytnij do typu regulatora ---
    params = _filter_for_regulator(regulator, pelne)

    # --- 3) zapisz JSON + raport HTML ---
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
