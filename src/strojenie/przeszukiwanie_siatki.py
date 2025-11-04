# src/strojenie/przeszukiwanie_siatki.py
"""
Przeszukiwanie siatki dla strojenia regulatorów PID/PI/PD/P.
Testuje wszystkie kombinacje parametrów w siatce używając prawdziwych symulacji.
"""
from itertools import product
from typing import Dict, Sequence
import numpy as np


def strojenie_siatka(RegulatorClass, model_nazwa: str, typ_regulatora: str, 
                     funkcja_symulacji_testowej):
    """
    Przeszukiwanie siatki z prawdziwymi symulacjami.
    
    Args:
        RegulatorClass: Klasa regulatora
        model_nazwa: nazwa modelu
        typ_regulatora: "regulator_p", "regulator_pi", "regulator_pd", "regulator_pid"
        funkcja_symulacji_testowej: funkcja (RegulatorClass, params, model_nazwa) -> (metryki, kara)
        
    Returns:
        dict: {"Kp": ..., "Ti": ..., "Td": ...}
    """
    print(f"🔍 Przeszukiwanie siatki dla {typ_regulatora} na modelu {model_nazwa}...")
    
    typ = typ_regulatora.lower()
    
    # Definicja siatek - RÓWNE WARUNKI dla wszystkich regulatorów
    # Wszyscy mają ten sam zakres i gęstość dla Kp
    if typ == "regulator_p":
        siatki = {
            "Kp": np.linspace(0.1, 15.0, 20)  # 20 punktów, zakres [0.1, 15.0]
        }
    elif typ == "regulator_pi":
        siatki = {
            "Kp": np.linspace(0.1, 15.0, 20),  # Ten sam zakres co P
            "Ti": np.linspace(2.0, 50.0, 15)   # Zakres zgodny z optymalizacją
        }
    elif typ == "regulator_pd":
        siatki = {
            "Kp": np.linspace(0.1, 15.0, 20),  # Ten sam zakres co P
            "Td": np.linspace(0.1, 15.0, 15)   # Zakres zgodny z optymalizacją
        }
    else:  # PID
        siatki = {
            "Kp": np.linspace(0.1, 15.0, 20),  # Ten sam zakres co P
            "Ti": np.linspace(2.0, 50.0, 12),  # Zakres zgodny z optymalizacją
            "Td": np.linspace(0.1, 15.0, 12)   # Zakres zgodny z optymalizacją
        }
    
    keys = list(siatki.keys())
    grids = [siatki[k] for k in keys]
    
    best_params = None
    best_kara = float("inf")
    total_tests = np.prod([len(g) for g in grids])
    test_count = 0
    
    print(f"📊 Testowanie {int(total_tests)} kombinacji parametrów...")
    
    # Przeszukuj wszystkie kombinacje
    for values in product(*grids):
        test_count += 1
        
        # Przygotuj parametry testowe
        params = {k: float(v) for k, v in zip(keys, values)}
        
        # Uzupełnij brakujące parametry (None dla nieużywanych)
        if "Ti" not in params:
            params["Ti"] = None
        if "Td" not in params:
            params["Td"] = None
        
        # Uruchom symulację testową
        try:
            _, kara = funkcja_symulacji_testowej(RegulatorClass, params, model_nazwa)
            
            # Aktualizuj najlepsze
            if kara < best_kara:
                best_kara = kara
                best_params = params.copy()
                print(f"  ✨ Nowy najlepszy wynik (test {test_count}/{int(total_tests)}): "
                      f"Kp={params['Kp']:.3f}, kara={kara:.2f}")
        
        except Exception as e:
            # Jeśli symulacja się wywalila (niestabilność), pomiń
            continue
    
    if best_params is None:
        print("⚠️ Nie znaleziono stabilnych parametrów, używam wartości domyślnych")
        best_params = {"Kp": 1.0, "Ti": 10.0 if typ in ["regulator_pi", "regulator_pid"] else None,
                       "Td": 3.0 if typ in ["regulator_pd", "regulator_pid"] else None}
    
    # Zaokrąglij wyniki
    result = {}
    for k in ["Kp", "Ti", "Td"]:
        val = best_params.get(k)
        result[k] = round(val, 4) if val is not None else None
    
    print(f"✅ Najlepsze parametry: Kp={result['Kp']}, Ti={result['Ti']}, Td={result['Td']}")
    return result


# Zachowaj starą funkcję dla kompatybilności
def przeszukiwanie_siatki(siatki: Dict[str, Sequence[float]], funkcja_celu):
    """
    Stara funkcja - uniwersalne przeszukiwanie siatki.
    Zachowana dla kompatybilności wstecznej.
    """
    if not siatki:
        raise ValueError("siatki nie może być puste")

    keys = list(siatki.keys())
    grids = [siatki[k] for k in keys]

    best_kwargs = None
    best_val = float("inf")

    for values in product(*grids):
        kwargs = {k: float(v) for k, v in zip(keys, values)}
        val = funkcja_celu(**kwargs)
        if val < best_val:
            best_val = val
            best_kwargs = kwargs

    return {k: round(v, 2) for k, v in best_kwargs.items()}
