"""
Moduł wywołujący różne metody strojenia regulatorów.
Zwraca zestaw parametrów do testów walidacyjnych i generuje raport HTML.
"""

import os
import json
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime

from src.strojenie.ziegler_nichols import strojenie_PID
from src.strojenie.przeszukiwanie_siatki import przeszukiwanie_siatki
from src.strojenie.optymalizacja_numeryczna import optymalizuj_podstawowy


def zapisz_raport_html(parametry, metoda, regulator, historia=None, out_dir="wyniki"):
    """
    Tworzy prosty raport HTML z wynikami strojenia.
    :param parametry: słownik parametrów PID
    :param metoda: nazwa metody strojenia
    :param regulator: typ regulatora (np. regulator_pid)
    :param historia: lista wartości funkcji celu (dla metod optymalizacji)
    :param out_dir: katalog docelowy
    """
    os.makedirs(out_dir, exist_ok=True)
    nazwa_html = f"raport_strojenie_{regulator}_{metoda}.html"
    html_path = os.path.join(out_dir, nazwa_html)

    with open(html_path, "w", encoding="utf-8") as f:
        f.write("<html><head><meta charset='utf-8'>")
        f.write(f"<title>Raport strojenia – {metoda.title()} ({regulator})</title>")
        f.write("<style>body{font-family:Arial,sans-serif;margin:20px;} "
                "table{border-collapse:collapse;} td,th{border:1px solid #aaa;padding:6px;} "
                "th{background:#ddd;} h2{color:#333;}</style></head><body>")

        f.write(f"<h2>📘 Raport strojenia – {regulator.upper()} (metoda: {metoda.title()})</h2>")
        f.write(f"<p>Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>")

        f.write("<table><tr><th>Parametr</th><th>Wartość</th></tr>")
        for k, v in parametry.items():
            f.write(f"<tr><td>{k}</td><td>{v}</td></tr>")
        f.write("</table>")

        # Dodaj wykres przebiegu optymalizacji, jeśli dostępny
        if historia and len(historia) > 1:
            plt.figure()
            plt.plot(historia, color='blue')
            plt.xlabel("Iteracja")
            plt.ylabel("Funkcja celu (IAE / błąd)")
            plt.title(f"Postęp optymalizacji – {metoda.title()} ({regulator})")
            wykres_path = os.path.join(out_dir, f"strojenie_{regulator}_{metoda}.png")
            plt.savefig(wykres_path, dpi=120)
            plt.close()
            f.write(f"<p><img src='strojenie_{regulator}_{metoda}.png' width='600'></p>")

        f.write("</body></html>")

    print(f"✅ Zapisano raport HTML: {html_path}")
    return html_path


def wykonaj_strojenie(metoda="ziegler_nichols", regulator="regulator_pid"):
    """
    Uruchamia proces strojenia zgodnie z wybraną metodą i typem regulatora.
    Zwraca słownik parametrów regulatora w formacie {'Kp', 'Ti', 'Td'}.
    """
    out_dir = "wyniki"
    historia = None

    # --- Wybór metody strojenia ---
    if metoda == "ziegler_nichols":
        print(f"⚙️ [{regulator}] Strojenie metodą Zieglera-Nicholsa...")
        parametry = strojenie_PID(Ku=2.0, Tu=25.0)

    elif metoda == "siatka":
        print(f"⚙️ [{regulator}] Strojenie metodą przeszukiwania siatki...")

        def funkcja_celu(kp, ti):
            return (kp - 2) ** 2 + (ti - 30) ** 2

        parametry = przeszukiwanie_siatki(
            np.linspace(0.5, 5, 10),
            np.linspace(5, 60, 10),
            lambda kp, ti: funkcja_celu(kp, ti)
        )

    elif metoda == "optymalizacja":
        print(f"⚙️ [{regulator}] Strojenie metodą optymalizacji numerycznej...")
        historia = []

        def funkcja_celu(x):
            wartosc = (x[0] - 2) ** 2 + (x[1] - 30) ** 2
            historia.append(wartosc)
            return wartosc

        parametry = optymalizuj_podstawowy(
            funkcja_celu,
            x0=[1, 20],
            granice=[(0.1, 10), (5, 100)]
        )

    else:
        raise ValueError(f"❌ Nieznana metoda strojenia: {metoda}")

    # --- Normalizacja formatu parametrów ---
    def normalizuj_parametry(param):
        """Zamienia wynik na słownik {'Kp','Ti','Td'} z zaokrągleniem do 2 miejsc."""
        def fmt(x):
            try:
                return round(float(x), 2)
            except Exception:
                return "-"

        if isinstance(param, dict):
            p = {k.lower(): v for k, v in param.items()}
            return {
                "Kp": fmt(p.get("kp") or p.get("k") or p.get("p")),
                "Ti": fmt(p.get("ti") or p.get("i") or p.get("taui")),
                "Td": fmt(p.get("td") or p.get("d") or p.get("taud")),
            }
        elif isinstance(param, (list, tuple)):
            vals = list(param) + ["-", "-", "-"]
            return {"Kp": fmt(vals[0]), "Ti": fmt(vals[1]), "Td": fmt(vals[2])}
        elif isinstance(param, (int, float, np.number)):
            return {"Kp": fmt(param), "Ti": "-", "Td": "-"}
        else:
            return {"Kp": "-", "Ti": "-", "Td": "-"}

    parametry_stand = normalizuj_parametry(parametry)

    # --- Dostosowanie do typu regulatora ---
    if "pi" in regulator.lower():
        parametry_stand["Td"] = "-"  # brak Td
    elif "dwupolozeniowy" in regulator.lower():
        parametry_stand = {"Kp": parametry_stand["Kp"], "Ti": "-", "Td": "-"}

    # --- Zapisz do pliku JSON ---
    os.makedirs(out_dir, exist_ok=True)
    json_path = os.path.join(out_dir, f"parametry_{regulator}_{metoda}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(parametry_stand, f, indent=2)
    print(f"💾 Zapisano parametry: {json_path}")

    # --- Raport HTML ---
    zapisz_raport_html(parametry_stand, metoda, regulator, historia, out_dir)

    return parametry_stand


if __name__ == "__main__":
    # Test lokalny – wykona strojenie wszystkimi metodami dla PID, PI i dwupołożeniowego
    for reg in ["regulator_pid", "regulator_pi", "regulator_dwupolozeniowy"]:
        for m in ["ziegler_nichols", "siatka", "optymalizacja"]:
            wykonaj_strojenie(m, reg)
