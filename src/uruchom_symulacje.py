# src/uruchom_symulacje.py
"""
Główny skrypt integrujący strojenie, walidację i raportowanie.
Dodano progi jakości (quality gates) dla automatycznej oceny PASS/FAIL.
"""

import os
import importlib
import json
import numpy as np
import matplotlib.pyplot as plt
from src.metryki import oblicz_metryki
from src.strojenie.wykonaj_strojenie import wykonaj_strojenie


def dynamiczny_import(typ: str, nazwa: str):
    """
    Dynamicznie importuje klasę modelu lub regulatora.
    """
    modul = importlib.import_module(f"src.{typ}.{nazwa}")
    klasa = None
    for attr in dir(modul):
        if attr.lower() == nazwa.lower():
            klasa = getattr(modul, attr)
            break
    if klasa is None:
        klasa = getattr(modul, [a for a in dir(modul) if not a.startswith("_")][0])
    return klasa


def uruchom_symulacje():
    """Główna pętla symulacji."""
    model_nazwa = os.getenv("MODEL", "zbiornik_1rz")
    regulator_nazwa = os.getenv("REGULATOR", "regulator_pid")
    czas_sym = float(os.getenv("CZAS_SYM", 60.0))
    dt = float(os.getenv("DT", 0.05))
    tryb = os.getenv("TRYB", "strojenie")  # "strojenie" lub "walidacja"
    out_dir = os.getenv("OUT_DIR", "wyniki")

    os.makedirs(out_dir, exist_ok=True)

    # --- Definicja progów jakości ---
    prog_overshoot = float(os.getenv("GATE_MAX_OVERSHOOT_PCT", 15.0))
    prog_settling = float(os.getenv("GATE_MAX_SETTLING_TIME", 30.0))
    prog_iae = float(os.getenv("GATE_MAX_IAE", 50.0))
    prog_ise = float(os.getenv("GATE_MAX_ISE", 100.0))

    # --- Tryb strojenia regulatora ---
    if tryb == "strojenie":
        for metoda in ["ziegler_nichols", "siatka", "optymalizacja"]:
            parametry = wykonaj_strojenie(metoda)
            with open(os.path.join(out_dir, f"parametry_{metoda}.json"), "w") as f:
                json.dump(parametry, f, indent=2)
        print("✅ Zakończono strojenie wszystkich metod.")
        return

    # --- Tryb walidacji regulatora ---
    elif tryb == "walidacja":
        metody = [f for f in os.listdir(out_dir) if f.startswith("parametry_")]
        if not metody:
            print("⚠️ Brak plików parametrów w katalogu:", out_dir)
            return

        for plik in metody:
            metoda = plik.split("_")[1].split(".")[0]
            with open(os.path.join(out_dir, plik), "r") as f:
                parametry = json.load(f)

            # Dynamiczny import modelu i regulatora
            Model = dynamiczny_import("modele", model_nazwa)
            Regulator = dynamiczny_import("regulatory", regulator_nazwa)
            model = Model(dt=dt)
            regulator = Regulator(**parametry, dt=dt)

            kroki = int(czas_sym / dt)
            t, r, y, u = [], [], [], []
            for k in range(kroki):
                t.append(k * dt)
                r_zad = 1.0
                y_k = model.y
                u_k = regulator.update(r_zad, y_k)
                y_nowe = model.step(u_k)
                r.append(r_zad)
                y.append(y_nowe)
                u.append(u_k)

            # Obliczenie metryk jakości
            wyniki = oblicz_metryki(t, r, y)

            # --- Ocena wg progów jakości ---
            pass_gates = True
            if wyniki.przeregulowanie > prog_overshoot:
                pass_gates = False
            if wyniki.czas_ustalania > prog_settling:
                pass_gates = False
            if wyniki.IAE > prog_iae:
                pass_gates = False
            if wyniki.ISE > prog_ise:
                pass_gates = False

            raport = {
                "model": model_nazwa,
                "regulator": regulator_nazwa,
                "metoda": metoda,
                "metryki": wyniki.__dict__,
                "progi": {
                    "overshoot_max": prog_overshoot,
                    "settling_max": prog_settling,
                    "IAE_max": prog_iae,
                    "ISE_max": prog_ise
                },
                "PASS": pass_gates
            }

            # Zapis raportu JSON
            raport_path = os.path.join(out_dir, f"raport_{metoda}.json")
            with open(raport_path, "w") as f:
                json.dump(raport, f, indent=2)

            # Wykres odpowiedzi skokowej
            plt.figure()
            plt.plot(t, r, label="wartość zadana (r)")
            plt.plot(t, y, label="odpowiedź układu (y)")
            plt.plot(t, u, label="sterowanie (u)")
            plt.xlabel("Czas [s]")
            plt.legend()
            plt.title(f"{metoda.upper()} — {model_nazwa} ({'PASS' if pass_gates else 'FAIL'})")
            plt.savefig(os.path.join(out_dir, f"wykres_{metoda}.png"), dpi=120, bbox_inches="tight")
            plt.close()

            # Log statusu
            status = "✅" if pass_gates else "❌"
            print(f"{status} Metoda {metoda} — IAE={wyniki.IAE:.2f}, overshoot={wyniki.przeregulowanie:.1f}%, ts={wyniki.czas_ustalania:.1f}s")

        print("✅ Zakończono walidację wszystkich metod.")
        return

    else:
        print("❌ Nieznany tryb działania (ustaw TRYB=strojenie lub walidacja).")


if __name__ == "__main__":
    uruchom_symulacje()
