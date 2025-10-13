# src/modele/zbiornik_1rz.py
from src.modele.model_bazowy import ModelBazowy

class Zbiornik_1rz(ModelBazowy):
    """
    Model pierwszego rzędu: G(s) = K / (τs + 1)
    """
    def __init__(self, K=1.0, tau=10.0, dt=0.05):
        super().__init__(dt)
        self.K = K
        self.tau = tau

    def step(self, u):
        dy = (-(self.y) + self.K * u) / self.tau
        self.y += self.dt * dy
        return self.y
