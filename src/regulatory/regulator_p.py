from src.regulatory.regulator_bazowy import RegulatorBazowy

class regulator_p(RegulatorBazowy):
    """
    Regulator P z kompensacją zadania (feed-forward/reference scaling),
    dzięki czemu przy stałym r odpowiedź dąży do 1 bez błędu ustalonego
    (dla G(0)≈1 wystarczy Kr=1.0).
    """
    def __init__(self, Kp: float = 1.0, Kr: float = 1.0, dt: float = 0.05, umin=None, umax=None):
        super().__init__(dt=dt, umin=umin, umax=umax)
        self.Kp = float(Kp)
        self.Kr = float(Kr)

    def update(self, r: float, y: float) -> float:
        e = r - y
        u = self.Kr * r + self.Kp * e
        u = self._saturate(u)
        self.u = u
        return u
