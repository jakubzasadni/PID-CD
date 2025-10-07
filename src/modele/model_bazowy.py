# src/modele/model_bazowy.py
"""
Klasa bazowa dla wszystkich modeli procesów.
Każdy model powinien dziedziczyć po BaseModel i implementować metodę step(u).
"""

class ModelBazowy:
    def __init__(self, dt: float = 0.05):
        """
        :param dt: krok czasowy symulacji [s]
        """
        self.dt = dt
        self.y = 0.0  # aktualna wartość wyjścia procesu

    def reset(self, y0: float = 0.0):
        """Resetuje stan modelu."""
        self.y = y0

    def step(self, u: float) -> float:
        """
        Jeden krok symulacji.
        :param u: sygnał sterujący
        :return: nowa wartość wyjścia procesu
        """
        raise NotImplementedError("Metoda step() musi zostać zaimplementowana w klasie pochodnej.")
