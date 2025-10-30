# src/regulatory/regulator_pid.py
from __future__ import annotations
from src.regulatory.regulator_bazowy import RegulatorBazowy


class Regulator_PID(RegulatorBazowy):
    """
    Discrete PID with:
      - derivative on measurement (anti-kick) with 1st-order filter,
      - output saturation and anti-windup (back-calculation),
      - optional clamp on derivative contribution (ud_max),
      - setpoint weighting in P path (beta) and bias u0.

    Control law (conceptual):
        u = u0 + Kp*(beta*r - y) + Ui - Ud

        dUi/dt = (Kp/Ti)*(r - y)
        Ud(s)  = (Td*s)/( (Td/N)*s + 1 ) * y   (filtered derivative of measurement)
                 (in time domain we use a standard recursive realization)

    Implementation details:
        - Euler integration for Ui
        - Back-calculation: Ui += (dt/Tt) * (u_sat - u_unsat)
        - Derivative filter:
            a = (Td/N) / ((Td/N) + dt)
            b = Td      / ((Td/N) + dt)
            Ud_k = a * Ud_{k-1} + b * (y_k - y_{k-1})/dt
        - If Ti <= 0 -> no integral; if Td <= 0 -> no derivative.
    """

    def __init__(
        self,
        kp: float = 1.0,
        ti: float = 30.0,
        td: float = 0.0,
        n: float = 30.0,            # derivative filter sharpness
        beta: float = 1.0,          # setpoint weight in P
        u0: float = 0.0,            # bias
        dt: float = 0.05,
        umin: float | None = 0.0,
        umax: float | None = 1.0,
        tt: float | None = None,    # anti-windup tracking time constant
        ud_max: float | None = None # clamp derivative contribution magnitude
    ):
        super().__init__(dt=dt, umin=umin, umax=umax)
        self.kp = float(kp)
        self.ti = float(ti)
        self.td = float(td)
        self.n = float(n)
        self.beta = float(beta)
        self.u0 = float(u0)

        # Anti-windup tuning
        self.tt = float(tt) if tt is not None else (self.ti/2.0 if self.ti > 0 else 1.0)

        # Derivative clamp
        self.ud_max = float(ud_max) if ud_max is not None else None

        # States
        self.ui = 0.0
        self.ud = 0.0
        self.prev_y = 0.0

    # ---------- helpers ----------
    def _clip(self, val: float) -> float:
        if self.umin is not None and val < self.umin:
            return self.umin
        if self.umax is not None and val > self.umax:
            return self.umax
        return val

    # ---------- API ----------
    def reset(self) -> None:
        super().reset()
        self.ui = 0.0
        self.ud = 0.0
        self.prev_y = 0.0

    def update(self, r: float, y: float) -> float:
        # P path (with setpoint weighting)
        up = self.kp * (self.beta * r - y)

        # --- Derivative on measurement ---
        if self.td > 0.0 and self.dt > 0.0:
            dy = (y - self.prev_y) / self.dt
            Td_over_N = self.td / max(self.n, 1e-9)
            a = Td_over_N / (Td_over_N + self.dt)
            b = self.td / (Td_over_N + self.dt)
            self.ud = a * self.ud + b * dy

            if self.ud_max is not None:
                if self.ud > self.ud_max:
                    self.ud = self.ud_max
                elif self.ud < -self.ud_max:
                    self.ud = -self.ud_max
        else:
            self.ud = 0.0

        # build unsaturated u from current integrator
        u_unsat = self.u0 + up + self.ui - self.ud

        # apply saturation
        u_sat = self._clip(u_unsat)

        # --- Integral with anti-windup ---
        if self.ti > 0.0:
            # normal Euler integration
            self.ui += (self.kp / self.ti) * (r - y) * self.dt
            # back-calculation correction
            self.ui += (self.dt / self.tt) * (u_sat - u_unsat)

            # rebuild with updated Ui (important after back-calculation)
            u_unsat = self.u0 + up + self.ui - self.ud
            u_sat = self._clip(u_unsat)

        # finalize
        self.u = u_sat
        self.prev_y = float(y)
        return self.u
