# src/regulatory/regulator_bazowy.py
"""
Klasa bazowa dla wszystkich regulatorów.
Każdy regulator powinien implementować metodę update(r, y),
gdzie r - wartość zadana, y - wartość zmierzona.
"""

class RegulatorBazowy:
    def __init__(self, dt: float = 0.05):
        self.dt = dt
        self.u = 0.0

    def reset(self):
        """Resetuje stan regulatora."""
        self.u = 0.0

    def update(self, r: float, y: float) -> float:
        """
        Aktualizuje sygnał sterujący na podstawie błędu e = r - y.
        :param r: wartość zadana
        :param y: wartość zmierzona
        :return: nowy sygnał sterujący u
        """
        raise NotImplementedError("Metoda update() musi zostać zaimplementowana w klasie pochodnej.")
