"""
Symulacja i walidacja dla wielu modeli procesów.
Walidacja używa plików parametry_{regulator}_{metoda}.json wygenerowanych w etapie 'strojenie'.
Obsługuje również tryb REGULATOR=all (P, PI, PD, PID).
"""

import os
import sys
import importlib
import json
import numpy as np
import matplotlib.pyplot as plt
from src.metryki import oblicz_metryki
from src.strojenie.wykonaj_strojenie import wykonaj_strojenie

# Bezpieczna konfiguracja wyjścia konsoli (Windows cp1250 vs emoji)
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


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
    czas_sym = float(os.getenv("CZAS_SYM", 120.0))
    tryb = os.getenv("TRYB", "strojenie")
    out_dir = os.getenv("OUT_DIR", "wyniki")
    model_env = os.getenv("MODEL", None)
    os.makedirs(out_dir, exist_ok=True)

    # Pobierz progi walidacji z config.yaml (v2.1)
    from src.konfig import pobierz_konfiguracje
    config = pobierz_konfiguracje()
    progi_config = config.pobierz_progi_walidacji()
    
    # Ujednolicone progi dla wszystkich modeli z config.yaml
    progi_modele = {
        "zbiornik_1rz": {"ts": progi_config["czas_ustalania_max"], 
                         "IAE": progi_config["IAE_max"], 
                         "Mp": progi_config["przeregulowanie_max"]},
        "dwa_zbiorniki": {"ts": progi_config["czas_ustalania_max"], 
                          "IAE": progi_config["IAE_max"], 
                          "Mp": progi_config["przeregulowanie_max"]},
        "wahadlo_odwrocone": {"ts": progi_config["czas_ustalania_max"], 
                              "IAE": progi_config["IAE_max"], 
                              "Mp": progi_config["przeregulowanie_max"]},
    }
    modele = [model_env] if model_env else list(progi_modele.keys())

    print(f" Wybrany regulator (env): {regulator_env}")
    print("🧱 Modele procesów:", ", ".join(modele))
    print("--------------------------------------------------")

    # -----------------------------------------------------
    # [1] Tryb strojenia
    # -----------------------------------------------------
    if tryb == "strojenie":
        print("[STROJENIE] [1/3] Strojenie metodami klasycznymi i optymalizacyjnymi...")

        # --- Obsługa trybu ALL (dla wszystkich regulatorów) ---
        if regulator_env.lower() == "all":
            regulatory_lista = ["regulator_p", "regulator_pi", "regulator_pd", "regulator_pid"]
        else:
            regulatory_lista = [regulator_env]

        # Dla każdego regulatora i modelu
        for regulator_nazwa in regulatory_lista:
            os.environ["REGULATOR"] = regulator_nazwa
            
            # Stroij na każdym modelu osobno
            for model_nazwa in modele:
                print(f"\n[STROJENIE] Strojenie regulatora: {regulator_nazwa} na modelu {model_nazwa}")
                for metoda in ["ziegler_nichols", "siatka", "optymalizacja"]:
                    print(f"  [ANALIZA] Metoda: {metoda.replace('_', ' ').title()}...")
                    try:
                        wykonaj_strojenie(metoda, model_nazwa=model_nazwa)
                    except Exception as e:
                        print(f"  [X] Błąd podczas strojenia: {e}")

        print("[OK] Zakończono strojenie wszystkich regulatorów i metod.")
        return

    # -----------------------------------------------------
    # [2] Tryb walidacji
    # -----------------------------------------------------
    elif tryb == "walidacja":
        pliki_params = [f for f in os.listdir(out_dir) if f.startswith("parametry_") and f.endswith(".json")]
        if not pliki_params:
            print("[UWAGA] Brak plików parametrów w katalogu:", out_dir)
            return

        # --- Wybór zbioru regulatorów i modeli ---
        if regulator_env.lower() == "all":
            regulator_files = pliki_params
        else:
            regulator_files = [p for p in pliki_params if f"parametry_{regulator_env}_" in p]

        # Filtruj po modelu jeśli podano
        if model_env.lower() != "all":
            regulator_files = [p for p in regulator_files if p.endswith(f"_{model_env}.json")]

        if not regulator_files:
            print("[UWAGA] Nie znaleziono parametrów dla wskazanego REGULATOR i MODEL:", regulator_env, model_env)
            return

        pass_count = 0
        total_count = 0
        print("\n🧪 [2/3] Walidacja...")

        for plik in sorted(regulator_files):
            with open(os.path.join(out_dir, plik), "r") as f:
                blob = json.load(f)
            regulator_nazwa = blob["regulator"]
            metoda = blob["metoda"]
            model_nazwa = blob.get("model", "zbiornik_1rz")  # Fallback dla starych plików
            parametry = blob["parametry"]

            # Waliduj tylko dla tego konkretnego modelu
            total_count += 1
            prog = progi_modele[model_nazwa]
            print(f"\n[SZUKANIE] [{regulator_nazwa} | {metoda}] model {model_nazwa}")
            print(f"📏 Progi: ts ≤ {prog['ts']}s, IAE ≤ {prog['IAE']}, Mp ≤ {prog['Mp']}%")

            Model = dynamiczny_import("modele", model_nazwa)
            Regulator = dynamiczny_import("regulatory", regulator_nazwa)
            model = Model()
            dt = model.dt

            import inspect
            sig = inspect.signature(Regulator.__init__)
            parametry_filtr = {k: v for k, v in parametry.items() if k in sig.parameters}
            # Usuń limity saturacji - model zadba o fizyczne ograniczenia
            regulator = Regulator(**parametry_filtr, dt=dt, umin=-15.0, umax=15.0)

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

            wyniki = oblicz_metryki(t, r, y, u)

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

            # Tworzenie wykresu z dwoma osiami Y
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), height_ratios=[2, 1])
            fig.suptitle(f"{regulator_nazwa} / {metoda} — {model_nazwa}\n({'PASS' if pass_gates else 'FAIL'})", fontsize=12)
            
            # Górny wykres: odpowiedź układu
            ax1.plot(t, r, 'k--', label='Wartość zadana (r)', alpha=0.7)
            ax1.plot(t, y, 'b-', label='Odpowiedź układu (y)', linewidth=2)
            ax1.set_xlabel('Czas [s]')
            ax1.set_ylabel('Wartość')
            ax1.grid(True, alpha=0.3)
            ax1.legend(loc='upper right')
            
            # Dolny wykres: sygnał sterujący
            ax2.plot(t, u, 'r-', label='Sterowanie (u)', linewidth=1.5)
            ax2.set_xlabel('Czas [s]')
            ax2.set_ylabel('Sterowanie')
            ax2.grid(True, alpha=0.3)
            ax2.legend(loc='upper right')
            
            # Dodanie informacji o metrykach
            info_text = (
                f"IAE: {wyniki.IAE:.2f}\n"
                f"Mp: {wyniki.przeregulowanie:.1f}%\n"
                f"ts: {wyniki.czas_ustalania:.1f}s\n"
                f"tr: {wyniki.czas_narastania:.1f}s"
            )
            plt.figtext(0.02, 0.02, info_text, fontsize=8, 
                  bbox=dict(facecolor='white', alpha=0.8))
            
            plt.tight_layout()
            plt.savefig(os.path.join(out_dir, f"wykres_{regulator_nazwa}_{metoda}_{model_nazwa}.png"), 
                      dpi=150, bbox_inches='tight')
            plt.close()

            status = "[OK]" if pass_gates else "[X]"
            if pass_gates:
                pass_count += 1
                print(f"{status} Wyniki:")
                print(f"  • IAE={wyniki.IAE:.2f}, ITAE={wyniki.ITAE:.2f}")
                print(f"  • Mp={wyniki.przeregulowanie:.1f}%, ts={wyniki.czas_ustalania:.1f}s, tr={wyniki.czas_narastania:.1f}s")
            else:
                print(f"{status} Wyniki:")
                print(f"  • IAE={wyniki.IAE:.2f}, ITAE={wyniki.ITAE:.2f}")
                print(f"  • Mp={wyniki.przeregulowanie:.1f}%, ts={wyniki.czas_ustalania:.1f}s, tr={wyniki.czas_narastania:.1f}s")
                print(f"  [X] Niezaliczone kryteria: {', '.join(powod)}")

        print("\n--------------------------------------------------")
        print(f"[ANALIZA] Łącznie PASS: {pass_count}/{total_count} ({100*pass_count/total_count:.1f}%)")

        # === ROZSZERZONA WALIDACJA (opcjonalna) ===
        try:
            from src.walidacja_rozszerzona import walidacja_rozszerzona
            from src.konfig import pobierz_konfiguracje

            print("\n" + "="*60)
            print("🔬 Uruchamiam rozszerzoną walidację (wiele scenariuszy)...")
            print("="*60)

            # Waliduj tylko kombinacje które przeszły podstawową walidację
            for plik in sorted(regulator_files):
                with open(os.path.join(out_dir, plik), "r") as f:
                    blob = json.load(f)
                regulator_nazwa = blob["regulator"]
                metoda = blob["metoda"]
                model_nazwa = blob.get("model", "zbiornik_1rz")
                parametry = blob["parametry"]

                # Sprawdź czy przeszła podstawową walidację
                raport_path = os.path.join(out_dir, f"raport_{regulator_nazwa}_{metoda}_{model_nazwa}.json")
                if os.path.exists(raport_path):
                    with open(raport_path, "r") as f:
                        rb = json.load(f)
                    if rb.get("PASS", False):
                        walidacja_rozszerzona(regulator_nazwa, metoda, model_nazwa, parametry, out_dir)
                    else:
                        print(f"  [SKIP] Pomijam rozszerzoną walidację dla {regulator_nazwa} / {metoda} / {model_nazwa} (FAIL w podstawowej walidacji)")

        except Exception as e:
            print(f"[UWAGA] Rozszerzona walidacja nie powiodła się: {e}")

        # === RAPORTY PORÓWNAWCZE ===
        try:
            from src.strojenie.raport_porownawczy import generuj_raport_porownawczy

            print("\n" + "="*60)
            print("[ANALIZA] Generuję raporty porównawcze...")
            print("="*60)

            # Dla każdego regulatora i modelu
            regulatory_unikalne = set()
            for plik in regulator_files:
                with open(os.path.join(out_dir, plik), "r") as f:
                    blob = json.load(f)
                regulatory_unikalne.add(blob["regulator"])

            for regulator in sorted(regulatory_unikalne):
                for model in modele:
                    try:
                        generuj_raport_porownawczy(regulator, model, out_dir)
                    except Exception as e:
                        print(f"[UWAGA] Nie udało się wygenerować raportu dla {regulator}/{model}: {e}")

        except Exception as e:
            print(f"[UWAGA] Generowanie raportów porównawczych nie powiodło się: {e}")

        if pass_count == 0:
            print("\n[X] Żaden regulator nie spełnił progów jakości.")
            exit(1)
        print("\n[OK] Walidacja zakończona.")
        return

    # -----------------------------------------------------
    # [3] Inny tryb (błąd)
    # -----------------------------------------------------
    else:
        print("[X] Nieznany tryb działania (TRYB=strojenie|walidacja)")


if __name__ == "__main__":
    uruchom_symulacje()
