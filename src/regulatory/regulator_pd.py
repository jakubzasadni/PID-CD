# src/regulatory/regulator_pd.py
from __future__ import annotations
from src.regulatory.regulator_bazowy import RegulatorBazowy


class Regulator_PD(RegulatorBazowy):
    """
    Discrete PD controller with:
      - derivative on measurement (anti-kick) with 1st-order filter,
      - optional derivative clamp (ud_max),
      - proportional setpoint weighting (alpha),
      - optional feed-forward term Kr*r to remove steady-state error
        for type-0 plants without using integral action,
      - output saturation (umin/umax).

    Control law (conceptual):
        u = u0 + Kr*r + Kp*(alpha*r - y) - Ud
        Ud(s) = (Td*s) / ((Td/N)*s + 1) * y   (filtered derivative of measurement)

    Notes:
        - Without integral action, a type-0 plant generally has steady-state error.
          Use Kr ≈ 1/K (K = plant DC gain) or a proper bias u0 to cancel it,
          provided the actuator is not saturated.
        - If Td <= 0 -> no derivative term is applied.
    """

    def __init__(
        self,
        kp: float = 1.0,
        td: float = 0.0,
        n: float = 30.0,            # derivative filter sharpness (N >= 1)
        alpha: float = 1.0,         # setpoint weight in P path
        Kr: float = 0.0,            # feed-forward gain for reference (set Kr≈1/K to remove steady-state error)
        u0: float = 0.0,            # static bias
        dt: float = 0.05,
        umin: float | None = 0.0,
        umax: float | None = 1.0,
        ud_max: float | None = None # clamp magnitude of derivative contribution
    ):
        super().__init__(dt=dt, umin=umin, umax=umax)
        self.kp = float(kp)
        self.td = float(td)
        self.n = float(n)
        self.alpha = float(alpha)
        self.Kr = float(Kr)
        self.u0 = float(u0)

        self.ud_max = float(ud_max) if ud_max is not None else None

        # states
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
        self.ud = 0.0
        self.prev_y = 0.0

    def update(self, r: float, y: float) -> float:
        # P path with setpoint weighting
        up = self.kp * (self.alpha * r - y)

        # derivative on measurement (filtered)
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

        # feed-forward + bias
        uff = self.Kr * r + self.u0

        # unsaturated output
        u_unsat = uff + up - self.ud

        # saturation
        u_sat = self._clip(u_unsat)

        # finalize
        self.u = u_sat
        self.prev_y = float(y)
        return self.u
