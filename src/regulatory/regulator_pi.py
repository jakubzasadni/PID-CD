# src/regulatory/regulator_pi.py
from src.regulatory.regulator_bazowy import RegulatorBazowy

class Regulator_PI(RegulatorBazowy):
    """
    Klasyczny regulator PI.
    """
    def __init__(self, kp=1.0, ti=30.0, umin=0.0, umax=1.0, dt=0.05):
        super().__init__(dt)
        self.kp = kp
        self.ti = ti
        self.umin = umin
        self.umax = umax
        self.ui = 0.0

    def update(self, r, y):
        e = r - y
        self.ui += (self.kp / self.ti) * e * self.dt
        u = self.kp * e + self.ui
        return max(self.umin, min(self.umax, u))
