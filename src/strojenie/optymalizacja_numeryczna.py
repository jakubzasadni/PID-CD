# src/strojenie/optymalizacja_numeryczna.py
"""
Optymalizacja numeryczna dla strojenia regulatorów PID/PI/PD/P.
Używa scipy.optimize.minimize z prawdziwymi symulacjami jako funkcją celu.
"""
from typing import Sequence, Iterable, Dict, Optional
from scipy.optimize import minimize


def strojenie_optymalizacja(RegulatorClass, model_nazwa: str, typ_regulatora: str,
                            funkcja_symulacji_testowej):
    """
    Optymalizacja numeryczna z prawdziwymi symulacjami.
    
    Args:
        RegulatorClass: Klasa regulatora
        model_nazwa: nazwa modelu
        typ_regulatora: "regulator_p", "regulator_pi", "regulator_pd", "regulator_pid"
        funkcja_symulacji_testowej: funkcja (RegulatorClass, params, model_nazwa) -> (metryki, kara)
        
    Returns:
        dict: {"Kp": ..., "Ti": ..., "Td": ...}
    """
    print(f"🔍 Optymalizacja numeryczna dla {typ_regulatora} na modelu {model_nazwa}...")
    
    typ = typ_regulatora.lower()
    historia = []  # Historia wartości funkcji celu
    
    # Definicja funkcji celu i parametrów startowych w zależności od typu regulatora
    # RÓWNE WARUNKI: Wszyscy startują z tych samych wartości bazowych
    if typ == "regulator_p":
        def funkcja_celu(x):
            params = {"Kp": x[0], "Ti": None, "Td": None}
            try:
                _, kara = funkcja_symulacji_testowej(RegulatorClass, params, model_nazwa)
                historia.append(kara)
                return kara
            except:
                return 999999.0
        
        x0 = [2.0]  # Ten sam Kp startowy co reszta
        granice = [(0.1, 15.0)]
        labels = ["Kp"]
    
    elif typ == "regulator_pi":
        def funkcja_celu(x):
            params = {"Kp": x[0], "Ti": x[1], "Td": None}
            try:
                _, kara = funkcja_symulacji_testowej(RegulatorClass, params, model_nazwa)
                historia.append(kara)
                return kara
            except:
                return 999999.0
        
        x0 = [2.0, 15.0]  # Start z typowych wartości PID
        granice = [(0.1, 15.0), (2.0, 50.0)]
        labels = ["Kp", "Ti"]
    
    elif typ == "regulator_pd":
        def funkcja_celu(x):
            params = {"Kp": x[0], "Ti": None, "Td": x[1]}
            try:
                _, kara = funkcja_symulacji_testowej(RegulatorClass, params, model_nazwa)
                historia.append(kara)
                return kara
            except:
                return 999999.0
        
        x0 = [2.0, 3.0]  # Start z typowych wartości PID
        granice = [(0.1, 15.0), (0.1, 15.0)]
        labels = ["Kp", "Td"]
    
    else:  # PID
        def funkcja_celu(x):
            params = {"Kp": x[0], "Ti": x[1], "Td": x[2]}
            try:
                _, kara = funkcja_symulacji_testowej(RegulatorClass, params, model_nazwa)
                historia.append(kara)
                print(f"    Iteracja {len(historia)}: Kp={x[0]:.3f}, Ti={x[1]:.3f}, Td={x[2]:.3f}, kara={kara:.2f}")
                return kara
            except:
                return 999999.0
        
        x0 = [2.0, 15.0, 3.0]  # Start z typowych wartości PID
        granice = [(0.1, 15.0), (2.0, 50.0), (0.1, 15.0)]
        labels = ["Kp", "Ti", "Td"]
    
    # Uruchom optymalizację
    print(f"🚀 Start optymalizacji z x0={x0}")
    res = minimize(funkcja_celu, x0, bounds=granice, method="L-BFGS-B", 
                   options={"maxiter": 50, "ftol": 1e-6})
    
    x_opt = res.x
    
    # Przygotuj wynik
    result = {}
    for i, name in enumerate(labels):
        result[name] = round(float(x_opt[i]), 4)
    
    # Uzupełnij brakujące parametry
    if "Ti" not in result:
        result["Ti"] = None
    if "Td" not in result:
        result["Td"] = None
    
    print(f"✅ Optymalizacja zakończona po {len(historia)} iteracjach")
    print(f"   Najlepsze parametry: Kp={result['Kp']}, Ti={result['Ti']}, Td={result['Td']}")
    print(f"   Najlepsza wartość funkcji celu: {res.fun:.2f}")
    
    return result, historia


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
