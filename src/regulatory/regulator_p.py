from src.regulatory.regulator_bazowy import RegulatorBazowy

class regulator_p(RegulatorBazowy):
    def __init__(self, Kp=1.0, dt=0.05):
        super().__init__(dt)
        self.Kp = float(Kp)

    def update(self, r, y):
        e = r - y
        u = self.Kp * e
        return u  # brak saturacji, czysty P
