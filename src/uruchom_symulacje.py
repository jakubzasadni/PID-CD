# src/uruchom_symulacje.py
"""
Symulacja i walidacja dla wielu modeli procesów.
Każda metoda strojenia testowana na wszystkich modelach.
Dodano progi jakości oraz walidację PASS/FAIL.
"""

import os
import importlib
import json
import numpy as np
import matplotlib.pyplot as plt
from src.metryki import oblicz_metryki
from src.strojenie.wykonaj_strojenie import wykonaj_strojenie


def dynamiczny_import(typ: str, nazwa: str):
    modul = importlib.import_module(f"src.{typ}.{nazwa}")
    for attr in dir(modul):
        if attr.lower() == nazwa.lower():
            return getattr(modul, attr)
    return getattr(modul, [a for a in dir(modul) if not a.startswith("_")][0])


def uruchom_symulacje():
    """Główna funkcja symulacji."""
    regulator_nazwa = os.getenv("REGULATOR", "regulator_pid")
    czas_sym = float(os.getenv("CZAS_SYM", 60.0))
    dt = float(os.getenv("DT", 0.05))
    tryb = os.getenv("TRYB", "strojenie")
    out_dir = os.getenv("OUT_DIR", "wyniki")
    os.makedirs(out_dir, exist_ok=True)

    # --- Dostępne modele ---
    modele = [
        "zbiornik_1rz",
        "dwa_zbiorniki",
        "wahadlo_odwrocone"
    ]

    # --- Progi jakości ---
    prog_overshoot = float(os.getenv("GATE_MAX_OVERSHOOT_PCT", 15.0))
    prog_settling = float(os.getenv("GATE_MAX_SETTLING_TIME", 30.0))
    prog_iae = float(os.getenv("GATE_MAX_IAE", 50.0))
    prog_ise = float(os.getenv("GATE_MAX_ISE", 100.0))

    if tryb == "strojenie":
        for metoda in ["ziegler_nichols", "siatka", "optymalizacja"]:
            parametry = wykonaj_strojenie(metoda)
            with open(os.path.join(out_dir, f"parametry_{metoda}.json"), "w") as f:
                json.dump(parametry, f, indent=2)
        print("✅ Zakończono strojenie wszystkich metod.")
        return

    elif tryb == "walidacja":
        metody = [f for f in os.listdir(out_dir) if f.startswith("parametry_")]
        if not metody:
            print("⚠️ Brak plików parametrów w katalogu:", out_dir)
            return

        all_pass = False  # globalny status walidacji

        for plik in metody:
            metoda = plik.split("_")[1].split(".")[0]
            with open(os.path.join(out_dir, plik), "r") as f:
                parametry = json.load(f)

            for model_nazwa in modele:
                print(f"🔍 Testowanie metody {metoda} na modelu {model_nazwa}...")

                Model = dynamiczny_import("modele", model_nazwa)
                Regulator = dynamiczny_import("regulatory", regulator_nazwa)
                model = Model(dt=dt)
                import inspect
                sig = inspect.signature(Regulator.__init__)
                parametry_filtr = {k: v for k, v in parametry.items() if k in sig.parameters}
                regulator = Regulator(**parametry_filtr, dt=dt)


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

                wyniki = oblicz_metryki(t, r, y)

                # --- Sprawdzenie progów jakości ---
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
                raport_path = os.path.join(out_dir, f"raport_{metoda}_{model_nazwa}.json")
                with open(raport_path, "w") as f:
                    json.dump(raport, f, indent=2)

                # Wykres
                plt.figure()
                plt.plot(t, r, label="wartość zadana (r)")
                plt.plot(t, y, label="odpowiedź układu (y)")
                plt.plot(t, u, label="sterowanie (u)")
                plt.xlabel("Czas [s]")
                plt.legend()
                plt.title(f"{metoda.upper()} — {model_nazwa} ({'PASS' if pass_gates else 'FAIL'})")
                plt.savefig(os.path.join(out_dir, f"wykres_{metoda}_{model_nazwa}.png"), dpi=120)
                plt.close()

                status = "✅" if pass_gates else "❌"
                print(f"{status} {metoda.upper()} — {model_nazwa}: IAE={wyniki.IAE:.2f}, Mp={wyniki.przeregulowanie:.1f}%, ts={wyniki.czas_ustalania:.1f}s")

                if pass_gates:
                    all_pass = True

        if not all_pass:
            print("❌ Żaden regulator nie spełnił progów jakości.")
            exit(1)

        print("✅ Wszystkie testy modeli zakończone. Wyniki zapisano.")
        return

    else:
        print("❌ Nieznany tryb działania (ustaw TRYB=strojenie lub walidacja).")


if __name__ == "__main__":
    uruchom_symulacje()
