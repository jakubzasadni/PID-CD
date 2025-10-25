"""
Symulacja i walidacja dla wielu modeli procesów.
Walidacja używa plików parametry_{regulator}_{metoda}.json wygenerowanych w etapie 'strojenie'.
Obsługuje również tryb REGULATOR=all (P, PI, PD, PID).
"""

import os
import importlib
import json
import numpy as np
import matplotlib.pyplot as plt
from src.metryki import oblicz_metryki
from src.strojenie.wykonaj_strojenie import wykonaj_strojenie


def dynamiczny_import(typ: str, nazwa: str):
    """Dynamicznie importuje klasę modelu lub regulatora po nazwie."""
    modul = importlib.import_module(f"src.{typ}.{nazwa}")
    for attr in dir(modul):
        if attr.lower() == nazwa.lower():
            return getattr(modul, attr)
    # fallback – zwraca pierwszą klasę nieukrytą
    return getattr(modul, [a for a in dir(modul) if not a.startswith("_")][0])


def uruchom_symulacje():
    regulator_env = os.getenv("REGULATOR", "regulator_pid")  # może być 'all'
    czas_sym = float(os.getenv("CZAS_SYM", 60.0))
    tryb = os.getenv("TRYB", "strojenie")
    out_dir = os.getenv("OUT_DIR", "wyniki")
    model_env = os.getenv("MODEL", None)
    os.makedirs(out_dir, exist_ok=True)

    progi_modele = {
        "zbiornik_1rz": {"ts": 60.0, "IAE": 50.0, "Mp": 15.0},
        "dwa_zbiorniki": {"ts": 80.0, "IAE": 80.0, "Mp": 20.0},
        "wahadlo_odwrocone": {"ts": 10.0, "IAE": 10.0, "Mp": 50.0},
    }
    modele = [model_env] if model_env else list(progi_modele.keys())

    print(f"🔧 Wybrany regulator (env): {regulator_env}")
    print("🧱 Modele procesów:", ", ".join(modele))
    print("--------------------------------------------------")

    # -----------------------------------------------------
    # 1️⃣ Tryb strojenia
    # -----------------------------------------------------
    if tryb == "strojenie":
        print("⚙️ [1/3] Strojenie metodami klasycznymi i optymalizacyjnymi...")

        # --- Obsługa trybu ALL (dla wszystkich regulatorów) ---
        if regulator_env.lower() == "all":
            regulatory_lista = ["regulator_p", "regulator_pi", "regulator_pd", "regulator_pid"]
        else:
            regulatory_lista = [regulator_env]

        for regulator_nazwa in regulatory_lista:
            os.environ["REGULATOR"] = regulator_nazwa
            print(f"\n⚙️ Strojenie regulatora: {regulator_nazwa}")
            for metoda in ["ziegler_nichols", "siatka", "optymalizacja"]:
                print(f"⚙️ Strojenie metodą {metoda.replace('_', ' ').title()}...")
                wykonaj_strojenie(metoda)

        print("✅ Zakończono strojenie wszystkich regulatorów i metod.")
        return

    # -----------------------------------------------------
    # 2️⃣ Tryb walidacji
    # -----------------------------------------------------
    elif tryb == "walidacja":
        pliki_params = [f for f in os.listdir(out_dir) if f.startswith("parametry_") and f.endswith(".json")]
        if not pliki_params:
            print("⚠️ Brak plików parametrów w katalogu:", out_dir)
            return

        # --- Wybór zbioru regulatorów ---
        if regulator_env.lower() == "all":
            regulator_files = pliki_params
        else:
            regulator_files = [p for p in pliki_params if f"parametry_{regulator_env}_" in p]

        if not regulator_files:
            print("⚠️ Nie znaleziono parametrów dla wskazanego REGULATOR:", regulator_env)
            return

        pass_count = 0
        total_count = 0
        print("\n🧪 [2/3] Walidacja...")

        for plik in sorted(regulator_files):
            with open(os.path.join(out_dir, plik), "r") as f:
                blob = json.load(f)
            regulator_nazwa = blob["regulator"]
            metoda = blob["metoda"]
            parametry = blob["parametry"]

            for model_nazwa in modele:
                total_count += 1
                prog = progi_modele[model_nazwa]
                print(f"\n🔍 [{regulator_nazwa} | {metoda}] model {model_nazwa}")
                print(f"📏 Progi: ts ≤ {prog['ts']}s, IAE ≤ {prog['IAE']}, Mp ≤ {prog['Mp']}%")

                Model = dynamiczny_import("modele", model_nazwa)
                Regulator = dynamiczny_import("regulatory", regulator_nazwa)
                model = Model()
                dt = model.dt

                import inspect
                sig = inspect.signature(Regulator.__init__)
                parametry_filtr = {k: v for k, v in parametry.items() if k in sig.parameters}
                regulator = Regulator(**parametry_filtr, dt=dt)

                kroki = int(czas_sym / dt)
                t, r, y, u = [], [], [], []

                for k in range(kroki):
                    t.append(k * dt)
                    r_zad = 0.0 if model_nazwa == "wahadlo_odwrocone" else 1.0
                    y_k = model.y
                    u_k = regulator.update(r_zad, y_k)
                    y_nowe = model.step(u_k)
                    r.append(r_zad)
                    y.append(y_nowe)
                    u.append(u_k)

                wyniki = oblicz_metryki(t, r, y)

                pass_gates = True
                powod = []
                if np.std(u) < 1e-4:
                    pass_gates = False
                    powod.append("brak reakcji regulatora (u ~ const)")
                if wyniki.przeregulowanie > prog["Mp"]:
                    pass_gates = False
                    powod.append("przeregulowanie")
                if wyniki.czas_ustalania > prog["ts"]:
                    pass_gates = False
                    powod.append("czas ustalania")
                if wyniki.IAE > prog["IAE"]:
                    pass_gates = False
                    powod.append("IAE")

                raport = {
                    "model": model_nazwa,
                    "regulator": regulator_nazwa,
                    "metoda": metoda,
                    "parametry": parametry,
                    "metryki": wyniki.__dict__,
                    "progi": prog,
                    "PASS": pass_gates,
                    "niezaliczone": powod,
                }

                raport_path = os.path.join(out_dir, f"raport_{regulator_nazwa}_{metoda}_{model_nazwa}.json")
                with open(raport_path, "w") as f:
                    json.dump(raport, f, indent=2)

                plt.figure()
                plt.plot(t, r, label="r")
                plt.plot(t, y, label="y")
                plt.plot(t, u, label="u")
                plt.xlabel("Czas [s]")
                plt.legend()
                plt.title(f"{regulator_nazwa} / {metoda} — {model_nazwa} ({'PASS' if pass_gates else 'FAIL'})")
                plt.savefig(os.path.join(out_dir, f"wykres_{regulator_nazwa}_{metoda}_{model_nazwa}.png"), dpi=120)
                plt.close()

                status = "✅" if pass_gates else "❌"
                if pass_gates:
                    pass_count += 1
                    print(f"{status} IAE={wyniki.IAE:.2f}, Mp={wyniki.przeregulowanie:.1f}%, ts={wyniki.czas_ustalania:.1f}s (OK)")
                else:
                    print(f"{status} IAE={wyniki.IAE:.2f}, Mp={wyniki.przeregulowanie:.1f}%, ts={wyniki.czas_ustalania:.1f}s ❌ {', '.join(powod)}")

        print("\n--------------------------------------------------")
        print(f"📊 Łącznie PASS: {pass_count}/{total_count} ({100*pass_count/total_count:.1f}%)")
        if pass_count == 0:
            print("❌ Żaden regulator nie spełnił progów jakości.")
            exit(1)
        print("✅ Walidacja zakończona.")
        return

    # -----------------------------------------------------
    # 3️⃣ Inny tryb (błąd)
    # -----------------------------------------------------
    else:
        print("❌ Nieznany tryb działania (TRYB=strojenie|walidacja)")


if __name__ == "__main__":
    uruchom_symulacje()
