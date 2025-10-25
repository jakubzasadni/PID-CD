from src.regulatory.regulator_bazowy import RegulatorBazowy

class regulator_pd(RegulatorBazowy):
    def __init__(self, Kp=1.0, Td=0.0, dt=0.05):
        super().__init__(dt)
        self.Kp = float(Kp)
        try:
            self.Td = float(Td)
        except ValueError:
            self.Td = 0.0
        self.prev_error = 0.0

    def update(self, r, y):
        e = r - y
        de = (e - self.prev_error) / self.dt
        u = self.Kp * (e + self.Td * de)
        self.prev_error = e
        return u
