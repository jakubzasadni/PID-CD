# src/strojenie/wykonaj_strojenie.py
"""
Moduł wywołujący różne metody strojenia regulatorów.
Zwraca zestaw parametrów do testów walidacyjnych.
"""

from src.strojenie.ziegler_nichols import strojenie_PID
from src.strojenie.przeszukiwanie_siatki import przeszukiwanie_siatki
from src.strojenie.optymalizacja_numeryczna import optymalizuj_podstawowy
import numpy as np

def wykonaj_strojenie(metoda="ziegler_nichols"):
    if metoda == "ziegler_nichols":
        print("⚙️ Strojenie metodą Zieglera-Nicholsa...")
        return strojenie_PID(Ku=2.0, Tu=25.0)

    elif metoda == "siatka":
        print("⚙️ Strojenie metodą przeszukiwania siatki...")
        def funkcja_celu(kp, ti): return (kp - 2)**2 + (ti - 30)**2
        return przeszukiwanie_siatki(np.linspace(0.5, 5, 10), np.linspace(5, 60, 10), lambda kp, ti: funkcja_celu(kp, ti))

    elif metoda == "optymalizacja":
        print("⚙️ Strojenie metodą optymalizacji numerycznej...")
        def funkcja_celu(x): return (x[0] - 2)**2 + (x[1] - 30)**2
        return optymalizuj_podstawowy(funkcja_celu, x0=[1, 20], granice=[(0.1, 10), (5, 100)])

    else:
        raise ValueError(f"Nieznana metoda strojenia: {metoda}")
