from src.regulatory.regulator_bazowy import RegulatorBazowy

class regulator_pd(RegulatorBazowy):
    """
    Regulator PD z reference-scaling (Kr). D = Kp*Td * de/dt.
    """
    def __init__(self, Kp: float = 1.0, Td: float = 0.0, Kr: float = 1.0, dt: float = 0.05, umin=None, umax=None):
        super().__init__(dt=dt, umin=umin, umax=umax)
        self.Kp = float(Kp)
        self.Td = float(Td)
        self.Kr = float(Kr)
        self._e_prev = 0.0

    def reset(self):
        super().reset()
        self._e_prev = 0.0

    def update(self, r: float, y: float) -> float:
        e = r - y
        de = (e - self._e_prev) / self.dt
        self._e_prev = e

        u = self.Kr * r + self.Kp * e + (self.Kp * self.Td) * de
        u = self._saturate(u)
        self.u = u
        return u
