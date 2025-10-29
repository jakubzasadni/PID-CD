# src/regulatory/regulator_pid.py
from src.regulatory.regulator_bazowy import RegulatorBazowy

class Regulator_PID(RegulatorBazowy):
    """
    Klasyczny regulator PID z prostym antywindupem.
    """
    def __init__(self, kp=1.0, ti=30.0, td=0.0, n=10.0, umin=0.0, umax=1.0, kaw=1.0, dt=0.05):
        super().__init__(dt)
        self.kp = kp
        self.ti = ti
        self.td = td
        self.n = n
        self.umin = umin
        self.umax = umax
        self.kaw = kaw
        self.ui = 0.0
        self.ud = 0.0
        self.prev_y = 0.0

    def update(self, r, y):
        e = r - y
        # Część całkująca
        self.ui += (self.kp / self.ti) * e * self.dt
        # Część różniczkująca
        self.ud = self.td / (self.td + self.n * self.dt) * self.ud + (self.kp * self.td * self.n) / (self.td + self.n * self.dt) * (y - self.prev_y)
        # Sygnał sterujący
        u_unsat = self.kp * e + self.ui - self.ud
        u_sat = max(self.umin, min(self.umax, u_unsat))
        # Antywindup
        self.ui += self.kaw * (u_sat - u_unsat)
        self.prev_y = y
        return u_sat
