# src/model.py
# First-order tank model: G(s) = K / (tau*s + 1)

from dataclasses import dataclass


@dataclass
class FirstOrderTank:
    K: float = 1.0 
    tau: float = 30.0
    dt: float = 0.05

    x: float = 0.0 
    y: float = 0.0
    def reset(self, y0: float = 0.0):
        self.x = y0
        self.y = y0

    def step(self, u: float) -> float:
        dx = (-(self.x) + self.K * u) / self.tau
        self.x += self.dt * dx
        self.y = self.x
        return self.y
