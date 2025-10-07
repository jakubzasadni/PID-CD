# src/uruchom_pipeline.py
"""
Uruchamia kompletny proces automatycznego strojenia, walidacji i oceny metod
dla wybranego regulatora. Regulator wybierany przez zmienną środowiskową REGULATOR.
"""

import os
import sys
sys.path.append("/app")
from src.uruchom_symulacje import uruchom_symulacje
from src.ocena_metod import ocena_metod
from datetime import datetime

def main():
    regulator = os.getenv("REGULATOR", "regulator_pid")
    model = os.getenv("MODEL", "zbiornik_1rz")
    print(f"🔧 Wybrany regulator: {regulator}")
    print(f"🧱 Model procesu: {model}")
    print("-" * 50)

    # Tworzenie folderu wyników z timestampem
    os.makedirs("wyniki", exist_ok=True)
    raport_folder = f"wyniki/{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    os.makedirs(raport_folder, exist_ok=True)
    os.environ["OUT_DIR"] = raport_folder

    # Etap 1: Strojenie
    print("⚙️ [1/3] Strojenie metodami klasycznymi i optymalizacyjnymi...")
    os.environ["TRYB"] = "strojenie"
    uruchom_symulacje()

    # Etap 2: Walidacja
    print("\n🧪 [2/3] Walidacja wszystkich metod...")
    os.environ["TRYB"] = "walidacja"
    os.environ["REGULATOR"] = regulator
    uruchom_symulacje()

    # Etap 3: Ocena
    print("\n📊 [3/3] Porównanie wyników i wybór najlepszego regulatora...")
    ocena_metod(raport_folder)

    print(f"\n✅ Pipeline zakończony pomyślnie. Wyniki zapisano w: {raport_folder}")

if __name__ == "__main__":
    main()
