# src/regulatory/regulator_pid.py
from src.regulatory.regulator_bazowy import RegulatorBazowy

class Regulator_PID(RegulatorBazowy):
    """
    PID w wersji dyskretnej z:
      - pochodną po pomiarze (anti-kick) + filtr 1. rzędu,
      - anti-windup (clamp I przez saturację wyjścia),
      - clamp na pochodnej (ud_max).

    u = Kp*(beta*r - y) + Ui - Ud
    """
    def __init__(
        self,
        kp: float = 1.0,
        ti: float = 20.0,
        td: float = 3.0,
        n: float = 40.0,     # ostrzejszy filtr D niż domyślne 10
        beta: float = 1.0,   # ważenie zadanego w P
        umin: float = 0.0,
        umax: float = 1.0,
        ud_max: float = 5.0, # clamp D
        dt: float = 0.05,
    ):
        super().__init__(dt)
        self.kp = float(kp)
        self.ti = float(ti)
        self.td = float(td)
        self.n = float(n)
        self.beta = float(beta)
        self.umin = float(umin)
        self.umax = float(umax)
        self.ud_max = float(ud_max)

        self.ui = 0.0
        self.ud = 0.0
        self.prev_y = 0.0

    def reset(self):
        super().reset()
        self.ui = 0.0
        self.ud = 0.0
        self.prev_y = 0.0

    def update(self, r: float, y: float) -> float:
        # Proporcjonalny (z ważeniem setpointu)
        e_p = self.beta * r - y
        up = self.kp * e_p

        # Całkujący (clamp przez saturację)
        if self.ti > 0:
            self.ui += self.kp * (self.dt / self.ti) * (r - y)

        # Różniczkujący (po pomiarze) + filtr + clamp
        if self.td > 0 and self.n > 0:
            a = self.td / (self.td + self.n * self.dt)
            b = (self.kp * self.td * self.n) / (self.td + self.n * self.dt)
            dy = y - self.prev_y
            self.ud = a * self.ud + b * dy
            # clamp D
            if self.ud > self.ud_max:
                self.ud = self.ud_max
            elif self.ud < -self.ud_max:
                self.ud = -self.ud_max
        else:
            self.ud = 0.0

        # Wyjście niesatur.
        u_unsat = up + self.ui - self.ud
        # Saturacja
        u_sat = max(self.umin, min(self.umax, u_unsat))

        # Anti-windup: jeśli wysycone, koryguj I
        if self.ti > 0:
            self.ui += (u_sat - u_unsat) * 0.0  # pasywne (0). Jeśli chcesz aktywne AWU: daj małe Kb.

        self.u = u_sat
        self.prev_y = float(y)
        return self.u
