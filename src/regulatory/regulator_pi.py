from typing import Optional

from src.regulatory.regulator_bazowy import RegulatorBazowy


class RegulatorPI(RegulatorBazowy):
    """Klasyczny regulator PI z anti-windup (back-calculation).

    Parametry:
        Kp: wzmocnienie proporcjonalne
        Ti: czas całkowania [s]
        kaw: wzmocnienie anty-windup (back-calculation)
    """
    def __init__(self, Kp: float = 1.0, Ti: float = 30.0, kaw: float = 0.1,
                 dt: float = 0.05, umin: Optional[float] = None, umax: Optional[float] = None):
        super().__init__(dt=dt, umin=umin, umax=umax)
        self.Kp = float(Kp)
        self.Ti = max(1e-6, float(Ti))
        self.kaw = float(kaw)
        self.ui = 0.0
        self.validate_params()

    def reset(self) -> None:
        super().reset()
        self.ui = 0.0

    def update(self, r: float, y: float) -> float:
        e = r - y
        # Proponowane u przed saturacją
        u_unsat = self.Kp * e + self.ui
        u_sat = self._saturate(u_unsat)

        # Anti-windup: back-calculation
        # Korekta całki proporcjonalna do różnicy (u_sat - u_unsat)
        self.ui += (self.Kp / self.Ti) * e * self.dt + self.kaw * (u_sat - u_unsat)

        # Zwróć wartość nasyconą
        self.u_prev = self.u
        self.u = u_sat
        return u_sat
