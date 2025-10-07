# src/strojenie/optymalizacja_numeryczna.py
from scipy.optimize import minimize

def optymalizuj_podstawowy(funkcja_celu, x0, granice):
    """
    Optymalizuje funkcję celu (np. IAE) metodą Neldera-Meada.
    """
    wynik = minimize(funkcja_celu, x0, bounds=granice, method="Nelder-Mead")
    return {"kp": wynik.x[0], "ti": wynik.x[1], "td": wynik.x[2] if len(wynik.x) > 2 else 0.0}
