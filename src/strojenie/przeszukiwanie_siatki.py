# src/strojenie/przeszukiwanie_siatki.py
"""
Przeszukiwanie siatki dla strojenia regulatorów PID/PI/PD/P.
Testuje wszystkie kombinacje parametrów w siatce używając prawdziwych symulacji.

Ulepszenia:
- Równoległe wykonywanie testów (joblib)
- Paski postępu (tqdm)
- Adaptacyjne zagęszczanie siatki (dwuetapowe: gruba -> dokładna)
- Konfiguracja z pliku config.yaml
"""
from itertools import product
from typing import Dict, Sequence, List, Tuple
import numpy as np
import logging
from tqdm import tqdm
from joblib import Parallel, delayed
import sys
import os

# Dodaj katalog src do PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from konfig import pobierz_konfiguracje


def _testuj_kombinacje(RegulatorClass, params: Dict, model_nazwa: str, 
                       funkcja_symulacji_testowej) -> Tuple[Dict, float]:
    """
    Pomocnicza funkcja do testowania pojedynczej kombinacji parametrów.
    Używana do równoległego wykonywania.
    
    Returns:
        (params, kara) lub (None, inf) jeśli symulacja się nie powiodła
    """
    try:
        _, kara = funkcja_symulacji_testowej(RegulatorClass, params, model_nazwa)
        return (params.copy(), kara)
    except Exception as e:
        logging.debug(f"Symulacja nieudana dla params={params}: {e}")
        return (None, float('inf'))


def _generuj_siatke(zakresy: Dict[str, Tuple[float, float]], 
                    gestosc: Dict[str, int],
                    typ_regulatora: str) -> Dict[str, np.ndarray]:
    """
    Generuje siatkę parametrów na podstawie zakresów i gęstości.
    
    Args:
        zakresy: {'Kp': (min, max), 'Ti': (min, max), 'Td': (min, max)}
        gestosc: {'Kp': n, 'Ti': m, 'Td': k}
        typ_regulatora: "regulator_p", "regulator_pi", "regulator_pd", "regulator_pid"
    
    Returns:
        Dict z numpy arrays dla każdego parametru
    """
    typ = typ_regulatora.lower()
    siatki = {}
    
    # Kp - zawsze używany
    siatki["Kp"] = np.linspace(zakresy["Kp"][0], zakresy["Kp"][1], gestosc["Kp"])
    
    # Ti - dla PI i PID
    if typ in ["regulator_pi", "regulator_pid"]:
        siatki["Ti"] = np.linspace(zakresy["Ti"][0], zakresy["Ti"][1], gestosc.get("Ti", 12))
    
    # Td - dla PD i PID
    if typ in ["regulator_pd", "regulator_pid"]:
        siatki["Td"] = np.linspace(zakresy["Td"][0], zakresy["Td"][1], gestosc.get("Td", 12))
    
    return siatki


def _zagesc_siatke_wokol_optimum(najlepsze_params: Dict, 
                                  zakresy_bazowe: Dict[str, Tuple[float, float]],
                                  gestosc: Dict[str, int],
                                  typ_regulatora: str,
                                  margines_procent: float = 0.2,
                                  mnoznik_gestosci: float = 1.5) -> Dict[str, np.ndarray]:
    """
    Generuje zagęszczoną siatkę wokół najlepszych parametrów z fazy grubej.
    
    Args:
        najlepsze_params: Najlepsze parametry z poprzedniej fazy
        zakresy_bazowe: Bazowe zakresy parametrów
        gestosc: Bazowa gęstość siatki
        typ_regulatora: Typ regulatora
        margines_procent: Margines wokół optimum (np. 0.2 = ±20%)
        mnoznik_gestosci: Jak bardzo zagęścić siatkę (np. 1.5 = 150% bazowej gęstości)
    
    Returns:
        Zagęszczona siatka wokół optimum
    """
    siatki_zageszczone = {}
    
    for param_name in najlepsze_params.keys():
        if najlepsze_params[param_name] is None:
            continue
        
        optymalna_wartosc = najlepsze_params[param_name]
        zakres_min, zakres_max = zakresy_bazowe[param_name]
        
        # Oblicz nowy zakres wokół optimum
        rozpiętość = zakres_max - zakres_min
        margines = rozpiętość * margines_procent
        
        nowy_min = max(zakres_min, optymalna_wartosc - margines)
        nowy_max = min(zakres_max, optymalna_wartosc + margines)
        
        # Zagęść siatkę
        liczba_punktow = int(gestosc.get(param_name, 12) * mnoznik_gestosci)
        siatki_zageszczone[param_name] = np.linspace(nowy_min, nowy_max, liczba_punktow)
        
        logging.info(f"  Zagęszczenie {param_name}: [{nowy_min:.2f}, {nowy_max:.2f}] "
                    f"z {liczba_punktow} punktami (wokół {optymalna_wartosc:.2f})")
    
    return siatki_zageszczone


def strojenie_siatka(RegulatorClass, model_nazwa: str, typ_regulatora: str, 
                     funkcja_symulacji_testowej):
    """
    Przeszukiwanie siatki z prawdziwymi symulacjami.
    
    Ulepszenia v2.0:
    - Równoległe wykonywanie
    - Paski postępu
    - Adaptacyjne zagęszczanie (opcjonalne)
    - Konfiguracja z config.yaml
    
    Args:
        RegulatorClass: Klasa regulatora
        model_nazwa: nazwa modelu
        typ_regulatora: "regulator_p", "regulator_pi", "regulator_pd", "regulator_pid"
        funkcja_symulacji_testowej: funkcja (RegulatorClass, params, model_nazwa) -> (metryki, kara)
        
    Returns:
        dict: {"Kp": ..., "Ti": ..., "Td": ...}
    """
    print(f"\n🔍 Przeszukiwanie siatki dla {typ_regulatora} na modelu {model_nazwa}...")
    
    # Wczytaj konfigurację
    config = pobierz_konfiguracje()
    zakresy = config.pobierz_zakresy(typ_regulatora, model_nazwa)
    gestosc = config.pobierz_gestosc_siatki(typ_regulatora)
    czy_adaptacyjne = config.czy_adaptacyjne_przeszukiwanie()
    czy_rownolegle = config.czy_rownolegle()
    n_jobs = config.pobierz_n_jobs()
    
    typ = typ_regulatora.lower()
    
    # ========== FAZA 1: GRUBA SIATKA (jeśli adaptacyjne) ==========
    if czy_adaptacyjne:
        print("📊 FAZA 1: Gruba siatka (szybkie przeszukanie)...")
        config_adaptacyjny = config.pobierz_config_adaptacyjny()
        mnoznik_grubej = config_adaptacyjny['faza_gruba']['gestosc_mnoznik']
        
        # Zmniejsz gęstość dla fazy grubej
        gestosc_gruba = {k: max(3, int(v * mnoznik_grubej)) for k, v in gestosc.items()}
        siatki = _generuj_siatke(zakresy, gestosc_gruba, typ_regulatora)
    else:
        # Pełna siatka od razu
        siatki = _generuj_siatke(zakresy, gestosc, typ_regulatora)
    
    # Przygotuj wszystkie kombinacje do testowania
    keys = list(siatki.keys())
    grids = [siatki[k] for k in keys]
    total_tests = int(np.prod([len(g) for g in grids]))
    
    print(f"  Testowanie {total_tests} kombinacji (równolegle={czy_rownolegle}, n_jobs={n_jobs})...")
    
    # Generuj listę wszystkich kombinacji parametrów
    kombinacje_params = []
    for values in product(*grids):
        params = {k: float(v) for k, v in zip(keys, values)}
        # Uzupełnij brakujące parametry
        if "Ti" not in params:
            params["Ti"] = None
        if "Td" not in params:
            params["Td"] = None
        kombinacje_params.append(params)
    
    # Testuj równolegle lub sekwencyjnie
    if czy_rownolegle and n_jobs != 1:
        # Równoległe wykonywanie
        wyniki = Parallel(n_jobs=n_jobs)(
            delayed(_testuj_kombinacje)(RegulatorClass, params, model_nazwa, funkcja_symulacji_testowej)
            for params in tqdm(kombinacje_params, desc="  Przeszukiwanie", unit="kombinacja")
        )
    else:
        # Sekwencyjne wykonywanie
        wyniki = []
        for params in tqdm(kombinacje_params, desc="  Przeszukiwanie", unit="kombinacja"):
            wynik = _testuj_kombinacje(RegulatorClass, params, model_nazwa, funkcja_symulacji_testowej)
            wyniki.append(wynik)
    
    # Znajdź najlepszy wynik
    best_params_faza1 = None
    best_kara_faza1 = float("inf")
    
    for params, kara in wyniki:
        if params is not None and kara < best_kara_faza1:
            best_kara_faza1 = kara
            best_params_faza1 = params
    
    if best_params_faza1 is None:
        print("⚠️ FAZA 1: Nie znaleziono stabilnych parametrów!")
        best_params_faza1 = {
            "Kp": 1.0, 
            "Ti": 10.0 if typ in ["regulator_pi", "regulator_pid"] else None,
            "Td": 3.0 if typ in ["regulator_pd", "regulator_pid"] else None
        }
    else:
        print(f"✅ FAZA 1 zakończona: Kp={best_params_faza1['Kp']:.3f}, kara={best_kara_faza1:.2f}")
    
    # ========== FAZA 2: ZAGĘSZCZONA SIATKA (jeśli adaptacyjne) ==========
    if czy_adaptacyjne:
        print("\n📊 FAZA 2: Zagęszczona siatka (dokładne przeszukanie wokół optimum)...")
        config_adaptacyjny = config.pobierz_config_adaptacyjny()
        margines = config_adaptacyjny['faza_dokladna']['margines_procent']
        mnoznik_dokladnej = config_adaptacyjny['faza_dokladna']['gestosc_mnoznik']
        
        # Wygeneruj zagęszczoną siatkę wokół najlepszego punktu z fazy 1
        siatki_faza2 = _zagesc_siatke_wokol_optimum(
            best_params_faza1, zakresy, gestosc, typ_regulatora,
            margines_procent=margines, mnoznik_gestosci=mnoznik_dokladnej
        )
        
        # Przygotuj kombinacje dla fazy 2
        keys_faza2 = list(siatki_faza2.keys())
        grids_faza2 = [siatki_faza2[k] for k in keys_faza2]
        total_tests_faza2 = int(np.prod([len(g) for g in grids_faza2]))
        
        print(f"  Testowanie {total_tests_faza2} kombinacji w zagęszczonym regionie...")
        
        kombinacje_params_faza2 = []
        for values in product(*grids_faza2):
            params = {k: float(v) for k, v in zip(keys_faza2, values)}
            if "Ti" not in params:
                params["Ti"] = None
            if "Td" not in params:
                params["Td"] = None
            kombinacje_params_faza2.append(params)
        
        # Testuj równolegle lub sekwencyjnie
        if czy_rownolegle and n_jobs != 1:
            wyniki_faza2 = Parallel(n_jobs=n_jobs)(
                delayed(_testuj_kombinacje)(RegulatorClass, params, model_nazwa, funkcja_symulacji_testowej)
                for params in tqdm(kombinacje_params_faza2, desc="  Zagęszczanie", unit="kombinacja")
            )
        else:
            wyniki_faza2 = []
            for params in tqdm(kombinacje_params_faza2, desc="  Zagęszczanie", unit="kombinacja"):
                wynik = _testuj_kombinacje(RegulatorClass, params, model_nazwa, funkcja_symulacji_testowej)
                wyniki_faza2.append(wynik)
        
        # Znajdź najlepszy wynik z fazy 2
        best_params = best_params_faza1
        best_kara = best_kara_faza1
        
        for params, kara in wyniki_faza2:
            if params is not None and kara < best_kara:
                best_kara = kara
                best_params = params
        
        if best_kara < best_kara_faza1:
            print(f"✅ FAZA 2: Znaleziono lepsze parametry! Poprawa: {best_kara_faza1:.2f} → {best_kara:.2f}")
        else:
            print(f"ℹ️ FAZA 2: Brak poprawy, pozostaję przy wynikach z fazy 1")
    else:
        # Brak adaptacyjnego zagęszczania
        best_params = best_params_faza1
        best_kara = best_kara_faza1
    
    # Zaokrąglij wyniki
    result = {}
    for k in ["Kp", "Ti", "Td"]:
        val = best_params.get(k)
        result[k] = round(val, 4) if val is not None else None
    
    print(f"\n✅ Najlepsze parametry (kara={best_kara:.2f}): Kp={result['Kp']}, Ti={result['Ti']}, Td={result['Td']}")
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
