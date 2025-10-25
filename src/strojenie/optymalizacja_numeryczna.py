from scipy.optimize import minimize

def optymalizuj_podstawowy(funkcja_celu, x0, granice):
    """
    Optymalizuje funkcję celu (np. IAE) metodą Neldera-Meada.
    Zwraca słownik z parametrami w ujednoliconym formacie: {"Kp", "Ti", "Td"}.
    """
    wynik = minimize(funkcja_celu, x0, bounds=granice, method="Nelder-Mead")
    x = wynik.x
    return {
        "Kp": round(float(x[0]), 4),
        "Ti": round(float(x[1]), 4),
        "Td": round(float(x[2]) if len(x) > 2 else 0.0, 4)
    }
