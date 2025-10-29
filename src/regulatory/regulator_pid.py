from math import isfinite
from src.regulatory.regulator_bazowy import RegulatorBazowy

class regulator_pid(RegulatorBazowy):
    """
    PID: P z ważeniem nastawy (beta), I ze „clamping” anti-windup,
    D od pomiaru + filtr 1-rzędu (bez derivative kick).
    Parametry: Kp, Ti, Td, beta (0..1), N (ostrość filtru D), umin/umax.
    """

    def __init__(self, Kp: float = 1.0, Ti: float = 30.0, Td: float = 3.0,
                 beta: float = 1.0, N: float = 10.0, dt: float = 0.05,
                 umin: float = float("-inf"), umax: float = float("inf")):
        super().__init__(dt=dt, umin=umin, umax=umax)
        self.Kp = float(Kp)
        self.Ti = max(1e-6, float(Ti))   # unikamy dzielenia przez 0
        self.Td = max(0.0, float(Td))
        self.beta = min(1.0, max(0.0, float(beta)))
        self.N = max(1.0, float(N))

        # stany
        self._ui = 0.0
        self._d_filt = 0.0
        self._y_prev = None
        self._alpha = 0.0 if self.Td == 0.0 else (self.dt * self.N) / (self.Td + self.dt * self.N)

    def reset(self):
        super().reset()
        self._ui = 0.0
        self._d_filt = 0.0
        self._y_prev = None

    def update(self, r: float, y: float) -> float:
        e = (r - y)

        # P z ważeniem nastawy (lepsze przy skoku r)
        up = self.Kp * (self.beta * r - y)

        # I z prostym „clamping” anti-windup
        ui_candidate = self._ui + self.Kp * (self.dt / self.Ti) * e

        # D od pomiaru + filtr 1-rzędu
        if self._y_prev is None or self.Td == 0.0:
            dy_dt = 0.0
        else:
            dy_dt = (y - self._y_prev) / self.dt
        raw_d = -dy_dt
        self._d_filt = self._lpf_step(self._d_filt, raw_d, self._alpha)
        ud = self.Kp * self.Td * self._d_filt

        # wstępne wyjście i saturacja
        u_unsat = up + ui_candidate + ud
        u_sat = self._saturate(u_unsat)

        # clamping: jeśli saturacja i integracja pogarsza sytuację – nie integruj
        if (u_unsat > self.umax and e > 0) or (u_unsat < self.umin and e < 0):
            # wycofaj krok integratora
            pass
        else:
            self._ui = ui_candidate

        self._y_prev = y
        self.u_prev = u_sat
        return u_sat
