from scipy.optimize import minimize

def optymalizuj_podstawowy(funkcja_celu, x0, granice):
    """
    Optymalizuje funkcję celu (np. IAE) metodą Neldera-Meada lub L-BFGS-B.
    Zwraca słownik zawierający tylko te parametry, które były optymalizowane:
    np. {'Kp': 1.5}, {'Kp': 2.0, 'Ti': 30.0}, {'Kp': 2.0, 'Td': 0.5}, {'Kp': 2.0, 'Ti': 30.0, 'Td': 3.0}.
    """
    wynik = minimize(funkcja_celu, x0, bounds=granice, method="Nelder-Mead")
    x = wynik.x

    # Tworzymy słownik zależnie od liczby zmiennych
    n = len(x)
    if n == 1:
        return {"Kp": round(float(x[0]), 4)}
    elif n == 2:
        return {"Kp": round(float(x[0]), 4), "Ti": round(float(x[1]), 4)}
    elif n == 3:
        return {"Kp": round(float(x[0]), 4), "Ti": round(float(x[1]), 4), "Td": round(float(x[2]), 4)}
    else:
        # fallback, jeśli przyszłościowo dodasz więcej zmiennych
        return {f"x{i}": round(float(v), 4) for i, v in enumerate(x)}
