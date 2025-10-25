from .regulator_bazowy import RegulatorBazowy

class regulator_p(RegulatorBazowy):
    def __init__(self, Kp=1.0, dt=0.01, **_):
        super().__init__(dt=dt)
        self.Kp = float(Kp)

    def update(self, r, y):
        e = r - y
        u = self.Kp * e
        return self._saturate(u)
