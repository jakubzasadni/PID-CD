# src/uruchom_pipeline.py
"""
Uruchamia kompletny proces automatycznego strojenia, walidacji i oceny metod
dla wybranego regulatora. Regulator wybierany przez zmienną środowiskową REGULATOR.

Wersja 2.1: Dodano automatyczne generowanie raportu końcowego (36 kombinacji).

Pipeline składa się z 4 etapów:
1. Strojenie - 3 metody (Ziegler-Nichols, siatka, optymalizacja)
2. Walidacja - testy na 3 modelach (zbiornik_1rz, dwa_zbiorniki, wahadlo_odwrocone)
3. Ocena - wybór najlepszego regulatora dla danego modelu
4. Raport końcowy - kompleksowa analiza wszystkich 36 kombinacji
"""

import os
import sys
sys.path.append("/app")
from src.uruchom_symulacje import uruchom_symulacje
from src.ocena_metod import ocena_metod
from src.metryki_pipeline import MetrykiPipeline
from src.raport_koncowy import GeneratorRaportuKoncowego
from datetime import datetime

def main():
    regulator = os.getenv("REGULATOR", "regulator_pid")
    model = os.getenv("MODEL", "zbiornik_1rz")
    print(f"Wybrany regulator: {regulator}")
    print(f"Model procesu: {model}")
    print("-" * 50)

    # Inicjalizacja metryk
    metryki = MetrykiPipeline()

    try:
        # Tworzenie folderu wyników z timestampem
        os.makedirs("wyniki", exist_ok=True)
        raport_folder = f"wyniki/{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        os.makedirs(raport_folder, exist_ok=True)
        os.environ["OUT_DIR"] = raport_folder

        # Etap 1: Strojenie
        with metryki.zmierz_etap("Strojenie regulatorów"):
            print("[1/4] Strojenie metodami klasycznymi i optymalizacyjnymi...")
            os.environ["TRYB"] = "strojenie"
            uruchom_symulacje()

        # Etap 2: Walidacja
        with metryki.zmierz_etap("Walidacja na modelach"):
            print("\n[2/4] Walidacja wszystkich metod...")
            os.environ["TRYB"] = "walidacja"
            os.environ["REGULATOR"] = regulator
            uruchom_symulacje()

        # Etap 3: Ocena
        with metryki.zmierz_etap("Ocena i porównanie metod"):
            print("\n[ANALIZA] [3/4] Porównanie wyników i wybór najlepszego regulatora...")
            ocena_metod(raport_folder)

        # Etap 4: Raport końcowy (36 kombinacji)
        with metryki.zmierz_etap("Generowanie raportu końcowego"):
            print("\n[RAPORT] [4/4] Generowanie kompleksowego raportu końcowego...")
            generator = GeneratorRaportuKoncowego(wyniki_dir="wyniki")
            raport_output = generator.generuj(output_dir=f"{raport_folder}/raport_koncowy")
            print(f"[OK] Raport końcowy zapisany w: {raport_output}")

        print(f"\n[OK] Pipeline zakończony pomyślnie. Wyniki zapisano w: {raport_folder}")
        
        # Zakończ pomiar i zapisz metryki
        metryki.zakoncz_run("success")
        
    except Exception as e:
        print(f"\n[X] Pipeline zakończony błędem: {e}")
        metryki.zakoncz_run("failed")
        raise
    
    finally:
        # Zawsze generuj raporty metryk
        metryki.generuj_badge_svg()
        metryki.generuj_raport_markdown()

if __name__ == "__main__":
    main()
