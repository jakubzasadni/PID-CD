from typing import Optional

from src.regulatory.regulator_bazowy import RegulatorBazowy


class RegulatorP(RegulatorBazowy):
    """Prosty regulator P z opcjonalnym feed-forward (Kr).

    Parametry:
        Kp: wzmocnienie proporcjonalne
        Kr: feed-forward (skalowanie wartości zadanej)
    """
    def __init__(self, Kp: float = 1.0, Kr: float = 1.0, dt: float = 0.05,
                 umin: Optional[float] = None, umax: Optional[float] = None):
        super().__init__(dt=dt, umin=umin, umax=umax)
        self.Kp = float(Kp)
        self.Kr = float(Kr)
        self.validate_params()

    def reset(self) -> None:
        super().reset()

    def update(self, r: float, y: float) -> float:
        e = r - y
        u_raw = self.Kr * r + self.Kp * e
        u = self._saturate(u_raw)
        self.u_prev = self.u
        self.u = u
        return u
