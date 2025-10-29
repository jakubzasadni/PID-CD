"""
Klasa bazowa dla wszystkich regulatorów.
Każdy regulator powinien implementować metodę update(r, y),
gdzie r - wartość zadana, y - wartość zmierzona.
"""

class RegulatorBazowy:
    def __init__(self, dt: float = 0.05, umin=None, umax=None):
        self.dt = float(dt)
        self.u = 0.0
        self.umin = umin
        self.umax = umax

    def reset(self):
        self.u = 0.0

    def _saturate(self, u: float) -> float:
        if self.umin is not None:
            u = max(self.umin, u)
        if self.umax is not None:
            u = min(self.umax, u)
        return u

    def update(self, r: float, y: float) -> float:
        raise NotImplementedError("Metoda update() musi zostać zaimplementowana w klasie pochodnej.")
