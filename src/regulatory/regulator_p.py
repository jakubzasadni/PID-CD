from src.regulatory.regulator_bazowy import RegulatorBazowy

class regulator_p(regulator_bazowy):
    def __init__(self, Kp=1.0, dt=0.01):
        super().__init__()
        self.Kp = float(Kp)
        self.dt = dt

    def update(self, r, y):
        e = r - y
        u = self.Kp * e
        return self._saturate(u)
