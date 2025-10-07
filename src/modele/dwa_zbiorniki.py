# src/modele/dwa_zbiorniki.py
from src.modele.model_bazowy import ModelBazowy

class Dwa_zbiorniki(ModelBazowy):
    """
    Model dwóch zbiorników w kaskadzie.
    """
    def __init__(self, K=1.0, tau1=20.0, tau2=10.0, dt=0.05):
        super().__init__(dt)
        self.K = K
        self.tau1 = tau1
        self.tau2 = tau2
        self.y1 = 0.0
        self.y2 = 0.0

    def step(self, u):
        dy1 = (-self.y1 + self.K * u) / self.tau1
        self.y1 += self.dt * dy1
        dy2 = (-self.y2 + self.y1) / self.tau2
        self.y2 += self.dt * dy2
        self.y = self.y2
        return self.y
