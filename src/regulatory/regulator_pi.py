# src/regulatory/regulator_pi.py
from __future__ import annotations
from src.regulatory.regulator_bazowy import RegulatorBazowy


class Regulator_PI(RegulatorBazowy):
    """
    Classic discrete PI controller with:
      - output saturation (umin/umax from base),
      - anti-windup (back-calculation),
      - optional "conditional integration" to avoid windup on hard saturation,
      - setpoint weighting in P path (beta).

    Control law (continuous-time idea):
        u = u0 + Kp*(beta*r - y) + Ui
        dUi/dt = (Kp/Ti) * (r - y)

    Discrete implementation:
        - Integrator is forward-Euler.
        - Anti-windup: Ui += (dt/Tt)*(u_sat - u_unsat)
        - Conditional integration (when enabled): integrate only if
          not saturated OR error tends to drive u back from saturation.

    Notes:
        - If Ti <= 0, integral action is disabled.
        - If u is limited by umax/umin and plant DC gain < 1, the system
          may never reach r=1. This is physically correct: actuator limit dominates.
    """

    def __init__(
        self,
        kp: float = 1.0,
        ti: float = 30.0,
        beta: float = 1.0,
        u0: float = 0.0,
        dt: float = 0.05,
        umin: float | None = 0.0,
        umax: float | None = 1.0,
        tt: float | None = None,               # tracking time const for back-calculation (anti-windup)
        conditional_integration: bool = False, # integrate only when safe
    ):
        super().__init__(dt=dt, umin=umin, umax=umax)
        self.kp = float(kp)
        self.ti = float(ti)
        self.beta = float(beta)
        self.u0 = float(u0)

        # Anti-windup tuning
        self.tt = float(tt) if tt is not None else (self.ti/2.0 if self.ti > 0 else 1.0)
        self.conditional_integration = bool(conditional_integration)

        # States
        self.ui = 0.0

    # ---------- helpers ----------
    def _clip(self, val: float) -> float:
        # same as _saturate from base, but inlined for speed/readability
        if self.umin is not None and val < self.umin:
            return self.umin
        if self.umax is not None and val > self.umax:
            return self.umax
        return val

    # ---------- API ----------
    def reset(self) -> None:
        super().reset()
        self.ui = 0.0

    def update(self, r: float, y: float) -> float:
        # proportional path uses weighted setpoint to avoid large P kick
        up = self.kp * (self.beta * r - y)

        # build unsaturated control from current integrator
        u_unsat = self.u0 + up + self.ui

        # apply saturation
        u_sat = self._clip(u_unsat)

        # integral update
        if self.ti > 0.0:
            if self.conditional_integration:
                # integrate only if not saturated, or if the error drives control back from saturation
                e = r - y
                integrate = (u_sat == u_unsat) \
                            or ((u_sat >= self.umax if self.umax is not None else False) and (self.kp * e) < 0.0) \
                            or ((u_sat <= self.umin if self.umin is not None else False) and (self.kp * e) > 0.0)
                if integrate:
                    self.ui += (self.kp / self.ti) * (r - y) * self.dt
            else:
                # standard back-calculation (tracking) anti-windup
                # first normal Euler integration
                self.ui += (self.kp / self.ti) * (r - y) * self.dt
                # then back-calculation correction
                self.ui += (self.dt / self.tt) * (u_sat - u_unsat)

            # rebuild with updated Ui (important if back-calculation changed it)
            u_unsat = self.u0 + up + self.ui
            u_sat = self._clip(u_unsat)

        self.u = u_sat
        return self.u
