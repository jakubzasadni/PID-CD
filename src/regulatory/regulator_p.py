from src.regulatory.regulator_bazowy import RegulatorBazowy


class regulator_p(RegulatorBazowy):
    """
    Regulator P (proporcjonalny):
    - Proporcjonalne na ważone zadanie: u_P = Kp * (b*r - y)
    - Feedforward Kr*r dla eliminacji offsetu stałego (domyślnie Kr=1.0)
    
    Parametry:
    - Kp: wzmocnienie proporcjonalne (domyślnie 1.0)
    - b:  waga wartości zadanej w członie P (domyślnie 1.0)
    - Kr: wzmocnienie feedforward (domyślnie 1.0) — kompensuje offset
    - dt: krok próbkowania (domyślnie 0.05)
    - umin, umax: ograniczenia sygnału sterującego (domyślnie None)
    
    Nieużywane w P (dla kompatybilności z PI/PD/PID):
    - Ti, Td, N, Tt (ignorowane)
    """

    def __init__(
        self,
        Kp: float = 1.0,
        Ti: float | None = None,
        Td: float | None = None,
        dt: float = 0.05,
        umin=None,
        umax=None,
        b: float = 1.0,
        Kr: float = 1.0,
        N: float | None = None,
        Tt: float | None = None,
    ):
        super().__init__(dt=dt, umin=umin, umax=umax)
        self.Kp = float(Kp)
        self.b = float(b)
        self.Kr = float(Kr)
        
        # Dla kompatybilności (nieużywane w P)
        self.Ti = Ti
        self.Td = Td
        self.N = N
        self.Tt = Tt

    def reset(self):
        super().reset()

    def update(self, r: float, y: float) -> float:
        # Część proporcjonalna z wagą b
        e_w = self.b * r - y
        u_p = self.Kp * e_w
        
        # Feedforward
        u_ff = self.Kr * r
        
        u = u_p + u_ff
        u = self._saturate(u)
        self.u = u
        return u
