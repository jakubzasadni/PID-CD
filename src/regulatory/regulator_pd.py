from typing import Optional
import math

from src.regulatory.regulator_bazowy import RegulatorBazowy


class RegulatorPD(RegulatorBazowy):
    """Regulator PD z reference-scaling (Kr) i filtrem różniczkującym.

    Parametry:
        Kp: wzmocnienie proporcjonalne
        Td: czas różniczkowania [s]
        Kr: feed-forward dla r
        N: współczynnik filtra D (ostrość)
    """
    def __init__(self, Kp: float = 1.0, Td: float = 0.0, Kr: float = 1.0,
                 dt: float = 0.05, umin: Optional[float] = None, umax: Optional[float] = None,
                 N: float = 10.0):
        super().__init__(dt=dt, umin=umin, umax=umax)
        self.Kp = float(Kp)
        self.Td = max(0.0, float(Td))
        self.Kr = float(Kr)
        self.N = max(1.0, float(N))

        self._e_prev = 0.0
        self._d_filt = 0.0
        self._filter_alpha = 0.0 if self.Td == 0.0 else (self.dt * self.N) / (self.Td + self.dt * self.N)
        self.validate_params()

    def reset(self) -> None:
        super().reset()
        self._e_prev = 0.0
        self._d_filt = 0.0

    def update(self, r: float, y: float) -> float:
        e = r - y
        # różniczkowanie po pomiarze (unikamy derivative kick)
        de = 0.0
        if hasattr(self, "_e_prev"):
            de = (e - self._e_prev) / self.dt
        self._e_prev = e

        # filtracja D (prosty LPF)
        raw_d = -de
        self._filter_alpha = 0.0 if self.Td == 0.0 else (self.dt * self.N) / (self.Td + self.dt * self.N)
        self._d_filt = self._d_filt + self._filter_alpha * (raw_d - self._d_filt)
        ud = self.Kp * self.Td * self._d_filt

        u_raw = self.Kr * r + self.Kp * e + ud
        # brak domyślnego rate limit -> użyj saturacji z bazy
        u = self._saturate(u_raw)
        self.u_prev = self.u
        self.u = u
        return u
