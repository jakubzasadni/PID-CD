# src/strojenie/optymalizacja_numeryczna.py
"""
Optymalizacja numeryczna dla strojenia regulatorów PID/PI/PD/P.
Używa scipy.optimize.minimize z prawdziwymi symulacjami jako funkcją celu.

Ulepszenia v2.0:
- Multi-start optymalizacja z losowych punktów
- Użycie wyników Ziegler-Nichols jako punktu startowego
- Paski postępu dla multi-start
- Konfiguracja z config.yaml
"""
from typing import Sequence, Iterable, Dict, Optional, List, Tuple
from scipy.optimize import minimize
import numpy as np
import logging
from tqdm import tqdm
import sys
import os

# Dodaj katalog src do PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from konfig import pobierz_konfiguracje


def _optymalizuj_z_punktu_startowego(
    funkcja_celu,
    x0: List[float],
    granice: List[Tuple[float, float]],
    labels: List[str],
    metoda: str = 'L-BFGS-B',
    maxiter: int = 500
) -> Tuple[Dict, float, List[float]]:
    """
    Pomocnicza funkcja wykonująca optymalizację z pojedynczego punktu startowego.
    
    Returns:
        (params_dict, best_value, historia)
    """
    historia = []
    
    def funkcja_z_historia(x):
        val = funkcja_celu(x)
        historia.append(val)
        return val
    
    try:
        res = minimize(
            funkcja_z_historia, 
            x0, 
            bounds=granice, 
            method=metoda,
            options={"maxiter": maxiter, "ftol": 1e-6}
        )
        
        result = {}
        for i, name in enumerate(labels):
            result[name] = round(float(res.x[i]), 4)
        
        return result, res.fun, historia
    except Exception as e:
        logging.warning(f"Optymalizacja z x0={x0} nie powiodła się: {e}")
        return None, float('inf'), []


def strojenie_optymalizacja(RegulatorClass, model_nazwa: str, typ_regulatora: str,
                            funkcja_symulacji_testowej, params_zn: Dict = None):
    """
    Optymalizacja numeryczna z prawdziwymi symulacjami.
    
    Ulepszenia v2.0:
    - Multi-start z losowych punktów
    - Użycie wyniku Ziegler-Nichols jako punktu startowego (opcjonalne)
    - Paski postępu
    - Konfiguracja z config.yaml
    
    Args:
        RegulatorClass: Klasa regulatora
        model_nazwa: nazwa modelu
        typ_regulatora: "regulator_p", "regulator_pi", "regulator_pd", "regulator_pid"
        funkcja_symulacji_testowej: funkcja (RegulatorClass, params, model_nazwa) -> (metryki, kara)
        params_zn: Parametry z Ziegler-Nichols (opcjonalne, użyte jako punkt startowy)
        
    Returns:
        dict: {"Kp": ..., "Ti": ..., "Td": ...}
    """
    print(f"\n[SZUKANIE] Optymalizacja numeryczna dla {typ_regulatora} na modelu {model_nazwa}...")
    
    # Wczytaj konfigurację
    config = pobierz_konfiguracje()
    zakresy = config.pobierz_zakresy(typ_regulatora, model_nazwa)
    config_opt = config.pobierz_config_optymalizacji()
    
    uzyj_zn = config_opt['punkty_startowe']['uzyj_ziegler_nichols']
    liczba_multi_start = config_opt['punkty_startowe']['liczba_multi_start']
    metoda = config_opt['punkty_startowe']['metoda']
    maxiter = config_opt['punkty_startowe']['maxiter']
    
    typ = typ_regulatora.lower()
    
    # Definicja funkcji celu i parametrów w zależności od typu regulatora
    if typ == "regulator_p":
        def funkcja_celu(x):
            params = {"Kp": x[0], "Ti": None, "Td": None}
            try:
                _, kara = funkcja_symulacji_testowej(RegulatorClass, params, model_nazwa)
                return kara
            except:
                return 999999.0
        
        granice = [(zakresy["Kp"][0], zakresy["Kp"][1])]
        labels = ["Kp"]
    
    elif typ == "regulator_pi":
        def funkcja_celu(x):
            params = {"Kp": x[0], "Ti": x[1], "Td": None}
            try:
                _, kara = funkcja_symulacji_testowej(RegulatorClass, params, model_nazwa)
                return kara
            except:
                return 999999.0
        
        granice = [(zakresy["Kp"][0], zakresy["Kp"][1]), 
                   (zakresy["Ti"][0], zakresy["Ti"][1])]
        labels = ["Kp", "Ti"]
    
    elif typ == "regulator_pd":
        def funkcja_celu(x):
            params = {"Kp": x[0], "Ti": None, "Td": x[1]}
            try:
                _, kara = funkcja_symulacji_testowej(RegulatorClass, params, model_nazwa)
                return kara
            except:
                return 999999.0
        
        granice = [(zakresy["Kp"][0], zakresy["Kp"][1]), 
                   (zakresy["Td"][0], zakresy["Td"][1])]
        labels = ["Kp", "Td"]
    
    else:  # PID
        def funkcja_celu(x):
            params = {"Kp": x[0], "Ti": x[1], "Td": x[2]}
            try:
                _, kara = funkcja_symulacji_testowej(RegulatorClass, params, model_nazwa)
                return kara
            except:
                return 999999.0
        
        granice = [(zakresy["Kp"][0], zakresy["Kp"][1]), 
                   (zakresy["Ti"][0], zakresy["Ti"][1]),
                   (zakresy["Td"][0], zakresy["Td"][1])]
        labels = ["Kp", "Ti", "Td"]
    
    # Przygotuj punkty startowe
    punkty_startowe = []
    
    # Punkt 1: Z Ziegler-Nichols (jeśli dostępne i włączone)
    if uzyj_zn and params_zn is not None:
        x0_zn = []
        for label in labels:
            val = params_zn.get(label)
            if val is not None:
                # Ogranicz do zakresu
                idx = labels.index(label)
                val = max(granice[idx][0], min(granice[idx][1], val))
                x0_zn.append(val)
            else:
                # Domyślna wartość jeśli brak w ZN
                idx = labels.index(label)
                x0_zn.append((granice[idx][0] + granice[idx][1]) / 2)
        
        punkty_startowe.append(("Ziegler-Nichols", x0_zn))
        print(f"  Punkt startowy 1: Ziegler-Nichols {x0_zn}")
    
    # Punkt 2: Domyślny (środek zakresu lub typowe wartości)
    x0_default = []
    for label in labels:
        idx = labels.index(label)
        if label == "Kp":
            x0_default.append(2.0)  # Typowa wartość
        elif label == "Ti":
            x0_default.append(15.0)  # Typowa wartość
        elif label == "Td":
            x0_default.append(3.0)  # Typowa wartość
    punkty_startowe.append(("Domyślny", x0_default))
    print(f"  Punkt startowy 2: Domyślny {x0_default}")
    
    # Punkty 3+: Losowe punkty startowe
    np.random.seed(42)  # Dla powtarzalności
    for i in range(liczba_multi_start):
        x0_losowy = []
        for bound in granice:
            # Losowa wartość z zakresu (log-uniform dla lepszego pokrycia)
            if bound[0] > 0:
                val = np.exp(np.random.uniform(np.log(bound[0]), np.log(bound[1])))
            else:
                val = np.random.uniform(bound[0], bound[1])
            x0_losowy.append(val)
        punkty_startowe.append((f"Losowy #{i+1}", x0_losowy))
        print(f"  Punkt startowy {i+3}: Losowy {[f'{v:.2f}' for v in x0_losowy]}")
    
    # Uruchom optymalizację z każdego punktu startowego
    print(f"\n[START] Uruchamiam {len(punkty_startowe)} optymalizacji (metoda={metoda}, maxiter={maxiter})...\n")
    
    wyniki = []
    wszystkie_historie = []
    
    for nazwa_punktu, x0 in tqdm(punkty_startowe, desc="Multi-start optymalizacja", unit="start"):
        result, best_val, historia = _optymalizuj_z_punktu_startowego(
            funkcja_celu, x0, granice, labels, metoda, maxiter
        )
        
        if result is not None:
            wyniki.append((nazwa_punktu, result, best_val, historia))
            wszystkie_historie.extend(historia)
            print(f"  ✓ {nazwa_punktu}: kara={best_val:.2f}, iteracji={len(historia)}")
        else:
            print(f"  ✗ {nazwa_punktu}: optymalizacja nieudana")
    
    # Wybierz najlepszy wynik
    if not wyniki:
        print("[UWAGA] Żadna optymalizacja nie powiodła się! Używam wartości domyślnych.")
        best_params = {
            "Kp": 1.0,
            "Ti": 10.0 if typ in ["regulator_pi", "regulator_pid"] else None,
            "Td": 3.0 if typ in ["regulator_pd", "regulator_pid"] else None
        }
        return best_params, []
    
    nazwa_najlepszego, best_params, best_val, _ = min(wyniki, key=lambda x: x[2])
    
    # Uzupełnij brakujące parametry
    if "Ti" not in best_params:
        best_params["Ti"] = None
    if "Td" not in best_params:
        best_params["Td"] = None
    
    print(f"\n[OK] Najlepszy wynik z punktu: {nazwa_najlepszego}")
    print(f"   Parametry: Kp={best_params['Kp']}, Ti={best_params['Ti']}, Td={best_params['Td']}")
    print(f"   Wartość funkcji celu: {best_val:.2f}")
    print(f"   Łącznie iteracji: {len(wszystkie_historie)}")
    
    # Porównaj wszystkie wyniki
    if len(wyniki) > 1:
        print(f"\n[ANALIZA] Porównanie wszystkich startów:")
        for nazwa, params, val, _ in sorted(wyniki, key=lambda x: x[2]):
            print(f"     {nazwa:20s}: kara={val:.2f}")
    
    return best_params, wszystkie_historie


# Zachowaj starą funkcję dla kompatybilności
def optymalizuj_podstawowy(
    funkcja_celu,
    x0: Sequence[float],
    granice: Optional[Sequence[tuple]] = None,
    labels: Optional[Iterable[str]] = None,
) -> Dict[str, float]:
    """
    Stara funkcja - minimalny wrapper na scipy.optimize.minimize.
    Zachowana dla kompatybilności wstecznej.
    """
    res = minimize(funkcja_celu, x0, bounds=granice, method="L-BFGS-B")
    x = res.x

    if labels is None:
        labels = []
        if len(x) >= 1: labels.append("Kp")
        if len(x) >= 2: labels.append("Ti")
        if len(x) >= 3: labels.append("Td")

    out: Dict[str, float] = {}
    for i, name in enumerate(labels):
        if i < len(x):
            out[name] = round(float(x[i]), 2)
    return out
