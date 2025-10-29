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


# ------------------------------------------------------------
# Pomocnicze funkcje formatowania i filtrowania
# ------------------------------------------------------------
def _get(params: dict, keys, default=None):
    for k in keys:
        if k in params:
            return params[k]
    return default


def _round_or_none(x, ndigits=2):
    if x is None:
        return None
    try:
        return round(float(x), ndigits)
    except Exception:
        return None


def _filter_for_regulator(reg_name: str, params: dict) -> dict:
    """Zwraca tylko te parametry, które mają sens dla danego typu regulatora."""
    reg = reg_name.lower()
    kp = _get(params, ["Kp", "kp"], 1.0)
    ti = _get(params, ["Ti", "ti"], None)
    td = _get(params, ["Td", "td"], None)

    if reg == "regulator_p":
        return {"Kp": _round_or_none(kp), "Ti": None, "Td": None}
    if reg == "regulator_pi":
        return {"Kp": _round_or_none(kp), "Ti": _round_or_none(ti), "Td": None}
    if reg == "regulator_pd":
        return {"Kp": _round_or_none(kp), "Ti": None, "Td": _round_or_none(td)}
    return {"Kp": _round_or_none(kp), "Ti": _round_or_none(ti), "Td": _round_or_none(td)}


# ------------------------------------------------------------
# Generacja raportu HTML
# ------------------------------------------------------------
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

        # Tabela parametrów
        f.write("<table><tr><th>Parametr</th><th>Wartość</th></tr>")
        for k in ["Kp", "Ti", "Td"]:
            val = parametry.get(k)
            f.write(f"<tr><td>{k}</td><td>{'-' if val is None else val}</td></tr>")
        f.write("</table>")

        # wykres postępu optymalizacji
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


# ------------------------------------------------------------
# Główna funkcja strojenia
# ------------------------------------------------------------
def wykonaj_strojenie(metoda="ziegler_nichols"):
    out_dir = "wyniki"
    os.makedirs(out_dir, exist_ok=True)

    regulator = os.getenv("REGULATOR", "regulator_pid").lower()
    historia = []

    # --- 1) Wyznacz parametry pełne (Kp, Ti, Td) ---
    if metoda == "ziegler_nichols":
        # ZN daje sensowne PID; dla PI/P/PD i tak przytniemy niżej
        pelne = strojenie_PID(Ku=2.0, Tu=25.0)  # -> Kp≈1.2, Ti≈12.5, Td≈3.12

    elif metoda == "siatka":
        # Siatki i funkcje celu dopasowane do typu regulatora
        if regulator == "regulator_p":
            pelne = przeszukiwanie_siatki(
                siatki={"Kp": np.linspace(0.5, 5.0, 20)},
                funkcja_celu=lambda Kp: (Kp - 2.0) ** 2
            )

        elif regulator == "regulator_pi":
            pelne = przeszukiwanie_siatki(
                siatki={"Kp": np.linspace(0.5, 5.0, 20),
                        "Ti": np.linspace(5, 60, 30)},
                funkcja_celu=lambda Kp, Ti: (Kp - 2.0) ** 2 + (Ti - 30.0) ** 2
            )

        elif regulator == "regulator_pd":
            pelne = przeszukiwanie_siatki(
                siatki={"Kp": np.linspace(0.5, 5.0, 20),
                        "Td": np.linspace(0.0, 10.0, 21)},
                funkcja_celu=lambda Kp, Td: (Kp - 2.0) ** 2 + (Td - 3.0) ** 2
            )

        else:  # PID
            pelne = przeszukiwanie_siatki(
                siatki={"Kp": np.linspace(0.5, 5.0, 20),
                        "Ti": np.linspace(5, 60, 30),
                        "Td": np.linspace(0.0, 10.0, 21)},
                funkcja_celu=lambda Kp, Ti, Td: (Kp - 2.0) ** 2 + (Ti - 30.0) ** 2 + (Td - 3.0) ** 2
            )

    elif metoda == "optymalizacja":
        # Definicje zależne od typu regulatora (różna liczba zmiennych i cel)
        if regulator == "regulator_p":
            def f(x):
                v = (x[0] - 2.0) ** 2; historia.append(v); return v
            x0, granice, labels = [1.0], [(0.1, 10)], ["Kp"]

        elif regulator == "regulator_pi":
            def f(x):
                v = (x[0] - 2.0) ** 2 + (x[1] - 30.0) ** 2; historia.append(v); return v
            x0, granice, labels = [1.0, 20.0], [(0.1, 10), (5, 100)], ["Kp", "Ti"]

        elif regulator == "regulator_pd":
            def f(x):
                v = (x[0] - 2.0) ** 2 + (x[1] - 3.0) ** 2; historia.append(v); return v
            # ⬇ KLUCZOWE: druga współrzędna to Td (etykieta 'Td')
            x0, granice, labels = [1.0, 1.0], [(0.1, 10), (0.0, 10.0)], ["Kp", "Td"]

        else:  # PID
            def f(x):
                v = (x[0] - 2.0) ** 2 + (x[1] - 30.0) ** 2 + (x[2] - 3.0) ** 2; historia.append(v); return v
            x0, granice, labels = [1.0, 20.0, 1.0], [(0.1, 10), (5, 100), (0.0, 10.0)], ["Kp", "Ti", "Td"]

        wynik = optymalizuj_podstawowy(f, x0, granice, labels=labels)
        print(f"🔍 Wynik optymalizacji dla {regulator}: {wynik}")

        # ujednolicenie formatu
        pelne = {
            "Kp": wynik.get("Kp", 1.0),
            "Ti": wynik.get("Ti", 30.0) if "Ti" in wynik else None,
            "Td": wynik.get("Td", 3.0) if "Td" in wynik else None
        }

    else:
        raise ValueError(f"❌ Nieznana metoda strojenia: {metoda}")

    # --- 2) Przytnij do typu regulatora i zaokrąglij ---
    params = _filter_for_regulator(regulator, pelne)

    # --- 3) Zapisz JSON + raport HTML ---
    meta = {"regulator": regulator, "metoda": metoda}
    out = {"regulator": regulator, "metoda": metoda, "parametry": params}

    json_path = os.path.join(out_dir, f"parametry_{regulator}_{metoda}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(f"💾 Zapisano parametry: {json_path}")

    _zapisz_raport_html(meta, params, historia, out_dir)
    return params


# ------------------------------------------------------------
# Test lokalny
# ------------------------------------------------------------
if __name__ == "__main__":
    for m in ["ziegler_nichols", "siatka", "optymalizacja"]:
        wykonaj_strojenie(m)
