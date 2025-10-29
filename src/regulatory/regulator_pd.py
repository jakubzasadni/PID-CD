# src/regulatory/regulator_pd.py
from src.regulatory.regulator_bazowy import RegulatorBazowy

class Regulator_PD(RegulatorBazowy):
    """
    Regulator PD:
      u = u0 + Kp * (beta*r - y) - Ud
    gdzie Ud to pochodna po POMIARZE z filtrem 1. rzędu (anti-kick).
    Dodatkowo: clamp na Ud (ud_max), by zbić szpilki sterowania.

    Parametry:
      kp   - wzmocnienie proporcjonalne
      td   - stała pochodnej [s]
      n    - „ostrość” filtra D (większe N = ostrzej, ale więcej szumu). 30–60 zwykle ok
      beta - ważenie zadanego w członie P (0..1). 1 => pełny skok P na r
      u0   - stała składowa/bias (np. do eliminacji uchybu dla PD)
      umin, umax - saturacje sterowania
      ud_max - clamp pochodnej (±ud_max)
      dt   - krok dyskretyzacji
    """
    def __init__(
        self,
        kp: float = 1.0,
        td: float = 3.0,
        n: float = 50.0,
        beta: float = 1.0,
        u0: float = 0.0,
        umin: float = 0.0,
        umax: float = 1.0,
        ud_max: float = 5.0,
        dt: float = 0.05,
    ):
        super().__init__(dt)
        self.kp = float(kp)
        self.td = float(td)
        self.n = float(n)
        self.beta = float(beta)
        self.u0 = float(u0)
        self.umin = float(umin)
        self.umax = float(umax)
        self.ud_max = float(ud_max)

        # stany wewnętrzne
        self.ud = 0.0
        self.prev_y = 0.0

    def reset(self):
        super().reset()
        self.ud = 0.0
        self.prev_y = 0.0

    def update(self, r: float, y: float) -> float:
        # P z ważeniem setpointu (ogranicza kick od r)
        e_p = self.beta * r - y
        up = self.kp * e_p

        # D po pomiarze, filtr 1. rzędu: Ud[k] = a*Ud[k-1] + b*(y[k]-y[k-1])
        if self.td > 0.0 and self.n > 0.0:
            a = self.td / (self.td + self.n * self.dt)
            b = (self.kp * self.td * self.n) / (self.td + self.n * self.dt)
            dy = y - self.prev_y
            self.ud = a * self.ud + b * dy

            # clamp na pochodnej (gasi szpilki)
            if self.ud > self.ud_max:
                self.ud = self.ud_max
            elif self.ud < -self.ud_max:
                self.ud = -self.ud_max
        else:
            self.ud = 0.0

        u_unsat = self.u0 + up - self.ud
        self.u = max(self.umin, min(self.umax, u_unsat))
        self.prev_y = float(y)
        return self.u
