# src/uruchom_pipeline.py
"""
Uruchamia kompletny proces automatycznego strojenia, walidacji i oceny metod
dla wybranego regulatora. Regulator wybierany przez zmienną środowiskową REGULATOR.
"""

import os
from datetime import datetime
from pathlib import Path
from src.uruchom_symulacje import uruchom_symulacje
from src.ocena_metod import ocena_metod

def main():
    # Konfiguracja z ENV
    regulator = os.getenv("REGULATOR", "regulator_pid")
    model = os.getenv("MODEL", "zbiornik_1rz")
    tryb = os.getenv("TRYB", "strojenie")
    print(f"Wybrany regulator: {regulator}")
    print(f"Model procesu: {model}")
    print(f"Tryb pracy: {tryb}")
    print("-" * 50)

    # Tworzenie folderu wyników z timestampem
    wyniki_dir = Path("wyniki")
    wyniki_dir.mkdir(parents=True, exist_ok=True)
    raport_folder = wyniki_dir / datetime.now().strftime("%Y%m%d_%H%M%S")
    raport_folder.mkdir(parents=True, exist_ok=True)

    # Etap 1: Strojenie
    print("[1/3] Strojenie metodami klasycznymi i optymalizacyjnymi...")
    reg1, mod1, params1, plot1, html1 = uruchom_symulacje(
        regulator_modul=regulator,
        model_modul=model,
        sciezka_cfg="src/konfiguracja.json",
        wyjscie_dir=raport_folder
    )

    # Etap 2: Walidacja
    print("\n[2/3] Walidacja wszystkich metod...")
    reg2, mod2, params2, plot2, html2 = uruchom_symulacje(
        regulator_modul=regulator,  # to samo co w kroku 1
        model_modul=model,
        sciezka_cfg="src/konfiguracja.json",
        wyjscie_dir=raport_folder
    )

    # Etap 3: Ocena
    print("\n📊 [3/3] Porównanie wyników i wybór najlepszego regulatora...")
    ocena_metod(raport_folder)

    print(f"\n✅ Pipeline zakończony pomyślnie. Wyniki zapisano w: {raport_folder}")

if __name__ == "__main__":
    main()
