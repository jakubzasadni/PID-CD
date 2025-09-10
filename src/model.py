# src/model.py
# First-order tank model: G(s) = K / (tau*s + 1)

from dataclasses import dataclass

@dataclass
class FirstOrderTank:
    K: float = 1.0     # static gain
    tau: float = 30.0  # time constant [s]
    dt: float = 0.05   # simulation step [s]

    x: float = 0.0     # internal state (approx. plant output)
    y: float = 0.0     # output

    def reset(self, y0: float = 0.0):
        self.x = y0
        self.y = y0

    def step(self, u: float) -> float:
        # Discrete-time update (forward Euler)
        dx = (-(self.x) + self.K * u) / self.tau
        self.x += self.dt * dx
        self.y = self.x
        return self.y
