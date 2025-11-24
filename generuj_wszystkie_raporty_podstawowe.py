"""
Skrypt do generowania raportów podstawowych dla wszystkich 36 kombinacji.
Uruchamia podstawową walidację (1 test standardowy) dla każdej kombinacji.
"""

import json
import sys
from pathlib import Path

# Importy z projektu
sys.path.insert(0, str(Path(__file__).parent / "src"))

from metryki import oblicz_metryki
from konfig import pobierz_konfiguracje
from uruchom_symulacje import dynamiczny_import

import numpy as np


def podstawowa_walidacja(ModelClass, RegulatorClass, parametry, model_nazwa, regulator_nazwa, metoda, katalog_wyniki="wyniki"):
    """
    Wykonuje podstawową walidację (1 test standardowy).
    Zwraca raport JSON gotowy do zapisu.
    """
    print(f"  Testowanie: {regulator_nazwa}/{metoda} na {model_nazwa}")
    
    # Pobierz konfigurację
    config = pobierz_konfiguracje()
    progi = config.pobierz_progi_walidacji()
    
    # Inicjalizacja modelu
    model = ModelClass()
    dt = model.dt
    
    # Filtrowanie parametrów regulatora
    import inspect
    sig = inspect.signature(RegulatorClass.__init__)
    parametry_filtr = {k: v for k, v in parametry.items() if k in sig.parameters}
    
    # Inicjalizacja regulatora
    regulator = RegulatorClass(**parametry_filtr, dt=dt, umin=None, umax=None)
    
    # Parametry symulacji
    czas_sym = 120.0
    kroki = int(czas_sym / dt)
    
    # Wartość zadana
    r_zad = 0.0 if model_nazwa == "wahadlo_odwrocone" else 1.0
    
    # Symulacja
    t, r, y, u = [], [], [], []
    
    for k in range(kroki):
        t.append(k * dt)
        y_k = model.y
        u_k = regulator.update(r_zad, y_k)
        y_nowe = model.step(u_k)
        
        r.append(r_zad)
        y.append(y_nowe)
        u.append(u_k)
    
    # Oblicz metryki
    wyniki = oblicz_metryki(t, r, y, u)
    
    # Sprawdź progi
    pass_gates = True
    powod = []
    
    # Sprawdź reakcję regulatora
    if np.std(u) < 1e-4:
        pass_gates = False
        powod.append("brak reakcji (u ~ const)")
    
    # Sprawdź metryki
    if wyniki.IAE > progi['IAE_max']:
        pass_gates = False
        powod.append(f"IAE={wyniki.IAE:.2f} > {progi['IAE_max']}")
    
    if wyniki.przeregulowanie > progi['przeregulowanie_max']:
        pass_gates = False
        powod.append(f"Mp={wyniki.przeregulowanie:.1f}% > {progi['przeregulowanie_max']}%")
    
    if wyniki.czas_ustalania > progi['czas_ustalania_max']:
        pass_gates = False
        powod.append(f"ts={wyniki.czas_ustalania:.1f}s > {progi['czas_ustalania_max']}s")
    
    # Przygotuj raport
    raport = {
        "model": model_nazwa,
        "regulator": regulator_nazwa,
        "metoda": metoda,
        "parametry": parametry,
        "metryki": wyniki.__dict__,
        "progi": progi,
        "PASS": pass_gates,
        "niezaliczone": powod
    }
    
    # Zapisz raport
    raport_path = Path(katalog_wyniki) / f"raport_{regulator_nazwa}_{metoda}_{model_nazwa}.json"
    with open(raport_path, "w", encoding="utf-8") as f:
        json.dump(raport, f, indent=2)
    
    status = "✓ PASS" if pass_gates else f"✗ FAIL ({', '.join(powod[:2])})"  # Pokaż max 2 powody
    print(f"    {status}")
    
    return raport


def main():
    """Generuje wszystkie 36 raportów podstawowych."""
    print("=" * 60)
    print("GENERATOR RAPORTÓW PODSTAWOWYCH (36 kombinacji)")
    print("=" * 60)
    
    # Listy kombinacji
    MODELE_NAZWY = ["zbiornik_1rz", "dwa_zbiorniki", "wahadlo_odwrocone"]
    REGULATORY_NAZWY = ["regulator_p", "regulator_pi", "regulator_pd", "regulator_pid"]
    METODY = ["ziegler_nichols", "siatka", "optymalizacja"]
    
    wyniki_dir = Path("wyniki")
    
    licznik = 0
    pass_count = 0
    fail_count = 0
    
    # Iteruj po wszystkich kombinacjach
    for regulator_nazwa in REGULATORY_NAZWY:
        for metoda in METODY:
            # Wczytaj parametry
            param_path = wyniki_dir / f"parametry_{regulator_nazwa}_{metoda}.json"
            
            if not param_path.exists():
                print(f"[SKIP] Brak parametrów: {param_path}")
                continue
            
            with open(param_path, "r", encoding="utf-8") as f:
                param_dane = json.load(f)
            
            # Wyciągnij właściwe parametry
            parametry = param_dane.get("parametry", param_dane)
            
            print(f"\n[{licznik+1}/36] {regulator_nazwa} / {metoda}")
            
            # Testuj na wszystkich 3 modelach
            for model_nazwa in MODELE_NAZWY:
                # Dynamiczny import
                ModelClass = dynamiczny_import("modele", model_nazwa)
                RegulatorClass = dynamiczny_import("regulatory", regulator_nazwa)
                
                raport = podstawowa_walidacja(
                    ModelClass, RegulatorClass, parametry,
                    model_nazwa, regulator_nazwa, metoda,
                    katalog_wyniki="wyniki"
                )
                
                licznik += 1
                if raport["PASS"]:
                    pass_count += 1
                else:
                    fail_count += 1
    
    print("\n" + "=" * 60)
    print(f"[OK] Wygenerowano {licznik} raportów podstawowych")
    print(f"  ✓ PASS: {pass_count}")
    print(f"  ✗ FAIL: {fail_count}")
    print("=" * 60)


if __name__ == "__main__":
    main()
