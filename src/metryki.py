# src/metryki.py
"""
Zbiór funkcji do obliczania wskaźników jakości regulacji.
"""

import numpy as np
from dataclasses import dataclass

@dataclass
class WynikiMetryk:
    IAE: float
    ISE: float
    przeregulowanie: float
    czas_ustalania: float


def oblicz_metryki(t, r, y, pasmo: float = 0.02) -> WynikiMetryk:
    """
    Oblicza podstawowe wskaźniki jakości:
    IAE - całka z wartości bezwzględnej błędu
    ISE - całka z kwadratu błędu
    przeregulowanie [%]
    czas ustalania [s]
    """
    e = np.array(r) - np.array(y)
    IAE = np.trapz(np.abs(e), t)
    ISE = np.trapz(e**2, t)

    y_ss = r[-1]
    przeregulowanie = max(0.0, (max(y) - y_ss) / y_ss * 100)

    # Czas ustalania - moment, gdy sygnał mieści się w ±pasmo przez resztę czasu
    granica_g = y_ss * (1 + pasmo)
    granica_d = y_ss * (1 - pasmo)
    czas_ustalania = t[-1]
    for i in range(len(y) - 1, 0, -1):
        if not (granica_d <= y[i] <= granica_g):
            czas_ustalania = t[i]
            break

    return WynikiMetryk(IAE, ISE, przeregulowanie, czas_ustalania)
