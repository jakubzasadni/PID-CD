from .regulator_bazowy import RegulatorBazowy

class regulator_pd(RegulatorBazowy):
    def __init__(self, Kp=1.0, Td=0.0, dt=0.01, **_):
        super().__init__(dt=dt)
        self.Kp = float(Kp)
        self.Td = float(Td)
        self._e_prev = 0.0

    def update(self, r, y):
        e = r - y
        de = (e - self._e_prev) / self.dt
        self._e_prev = e
        u = self.Kp * (e + self.Td * de)
        return self._saturate(u)
