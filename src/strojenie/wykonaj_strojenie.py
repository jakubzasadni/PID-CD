# src/strojenie/wykonaj_strojenie.py
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


def zapisz_raport_html(parametry, metoda, historia=None, out_dir="wyniki"):
    """
    Tworzy prosty raport HTML z wynikami strojenia.
    :param parametry: słownik parametrów PID
    :param metoda: nazwa metody strojenia
    :param historia: lista wartości funkcji celu (dla metod optymalizacji)
    :param out_dir: katalog docelowy
    """
    os.makedirs(out_dir, exist_ok=True)
    html_path = os.path.join(out_dir, f"raport_strojenie_{metoda}.html")

    with open(html_path, "w", encoding="utf-8") as f:
        f.write("<html><head><meta charset='utf-8'>")
        f.write(f"<title>Raport strojenia – {metoda.title()}</title>")
        f.write("<style>body{font-family:Arial,sans-serif;margin:20px;} "
                "table{border-collapse:collapse;} td,th{border:1px solid #aaa;padding:6px;} "
                "th{background:#ddd;} h2{color:#333;}</style></head><body>")

        f.write(f"<h2>📘 Raport strojenia – metoda: {metoda.title()}</h2>")
        f.write(f"<p>Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>")

        f.write("<table><tr><th>Parametr</th><th>Wartość</th></tr>")
        for k, v in parametry.items():
            f.write(f"<tr><td>{k}</td><td>{round(v, 6) if isinstance(v, float) else v}</td></tr>")
        f.write("</table>")

        # Dodaj wykres przebiegu optymalizacji, jeśli dostępny
        if historia and len(historia) > 1:
            plt.figure()
            plt.plot(historia, color='blue')
            plt.xlabel("Iteracja")
            plt.ylabel("Funkcja celu (IAE / błąd)")
            plt.title(f"Postęp optymalizacji – {metoda.title()}")
            wykres_path = os.path.join(out_dir, f"strojenie_{metoda}.png")
            plt.savefig(wykres_path, dpi=120)
            plt.close()
            f.write(f"<p><img src='strojenie_{metoda}.png' width='600'></p>")

        f.write("</body></html>")

    print(f"Zapisano raport HTML: {html_path}")
    return html_path


def wykonaj_strojenie(metoda="ziegler_nichols"):
    """
    Uruchamia proces strojenia zgodnie z wybraną metodą.
    Zwraca słownik parametrów regulatora.
    """
    out_dir = "wyniki"
    historia = None

    if metoda == "ziegler_nichols":
        print("⚙️ Strojenie metodą Zieglera-Nicholsa...")
        parametry = strojenie_PID(Ku=2.0, Tu=25.0)

    elif metoda == "siatka":
        print("⚙️ Strojenie metodą przeszukiwania siatki...")
        def funkcja_celu(kp, ti): return (kp - 2)**2 + (ti - 30)**2
        parametry = przeszukiwanie_siatki(
            np.linspace(0.5, 5, 10),
            np.linspace(5, 60, 10),
            lambda kp, ti: funkcja_celu(kp, ti)
        )

    elif metoda == "optymalizacja":
        print("⚙️ Strojenie metodą optymalizacji numerycznej...")
        historia = []
        def funkcja_celu(x):
            wartosc = (x[0] - 2)**2 + (x[1] - 30)**2
            historia.append(wartosc)
            return wartosc

        parametry = optymalizuj_podstawowy(
            funkcja_celu,
            x0=[1, 20],
            granice=[(0.1, 10), (5, 100)]
        )

    else:
        raise ValueError(f"❌ Nieznana metoda strojenia: {metoda}")

    # Zapisz wyniki do JSON
    os.makedirs(out_dir, exist_ok=True)
    json_path = os.path.join(out_dir, f"parametry_{metoda}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(parametry, f, indent=2)
    print(f"💾 Zapisano parametry: {json_path}")

    # Zapisz raport HTML
    zapisz_raport_html(parametry, metoda, historia, out_dir)

    return parametry


if __name__ == "__main__":
    # Test lokalny
    for m in ["ziegler_nichols", "siatka", "optymalizacja"]:
        wykonaj_strojenie(m)
