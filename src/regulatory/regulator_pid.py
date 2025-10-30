from typing import Optional
import math

from src.regulatory.regulator_bazowy import RegulatorBazowy


class RegulatorPID(RegulatorBazowy):
    """Klasyczny PID z kilkoma poprawkami: walidacja, reset, anti-windup.

    Params kept similar to original implementation for backward compatibility.
    """
    def __init__(self, kp: float = 1.0, ti: float = 30.0, td: float = 0.0,
                 n: float = 10.0, umin: Optional[float] = None, umax: Optional[float] = None,
                 kaw: float = 0.1, dt: float = 0.05):
        super().__init__(dt=dt, umin=umin, umax=umax)
        self.kp = float(kp)
        self.ti = max(1e-6, float(ti))
        self.td = max(0.0, float(td))
        self.n = max(1.0, float(n))
        self.kaw = float(kaw)

        # stany
        self.ui = 0.0
        self.ud = 0.0
        self.prev_y = None
        self._filter_alpha = 0.0 if self.td == 0.0 else (self.dt * self.n) / (self.td + self.dt * self.n)
        self.validate_params()

    def reset(self) -> None:
        super().reset()
        self.ui = 0.0
        self.ud = 0.0
        self.prev_y = None

    def update(self, r: float, y: float) -> float:
        e = r - y
        # Integrator
        self.ui += (self.kp / self.ti) * e * self.dt

        # Derivative (filterowany)
        if self.prev_y is None or self.td == 0.0:
            dy = 0.0
        else:
            dy = y - self.prev_y
        raw_d = (self.kp * self.td * self.n) / (self.td + self.n * self.dt) * dy
        # IIR-like update consistent with prior implementation
        self.ud = (self.td / (self.td + self.n * self.dt)) * self.ud + raw_d

        u_unsat = self.kp * e + self.ui - self.ud
        u_sat = self._saturate(u_unsat)

        # Anti-windup (back-calculation)
        self.ui += self.kaw * (u_sat - u_unsat)

        self.prev_y = y
        self.u_prev = self.u
        self.u = u_sat
        return u_sat
