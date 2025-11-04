from src.regulatory.regulator_bazowy import RegulatorBazowy


class regulator_pd(RegulatorBazowy):
    """
    Regulator PD (proporcjonalno-różniczkujący):
    - Proporcjonalne na ważone zadanie: u_P = Kp * (b*r - y)
    - Różniczkujące na pomiar (bez "derivative kick"), filtrowane (współczynnik N):
        v_d[k] = a * v_d[k-1] - beta * (y[k] - y[k-1])
        a    = Td / (Td + N*dt)
        beta = Kp * Td * N / (Td + N*dt)
    - Feedforward Kr*r dla eliminacji offsetu stałego (domyślnie Kr=1.0)

    Parametry:
    - Kp: wzmocnienie proporcjonalne (domyślnie 1.0)
    - Ti: nieużywane w PD (dla kompatybilności z PI/PID, domyślnie None)
    - Td: stała różniczkowania w sekundach (domyślnie 0.0)
    - N:  współczynnik filtra pochodnej (domyślnie 10.0)
    - b:  waga wartości zadanej w członie P (domyślnie 1.0)
    - Kr: wzmocnienie feedforward (domyślnie 1.0) — kompensuje offset
    - dt: krok próbkowania (domyślnie 0.05)
    - umin, umax: ograniczenia sygnału (domyślnie None)
    
    Nieużywane w PD (dla kompatybilności z PI/PID):
    - Ti, Tt (ignorowane)
    """

    def __init__(
        self,
        Kp: float = 1.0,
        Ti: float | None = None,
        Td: float = 0.0,
        dt: float = 0.05,
        umin=None,
        umax=None,
        b: float = 1.0,
        Kr: float = 1.0,
        N: float = 10.0,
        Tt: float | None = None,
    ):
        super().__init__(dt=dt, umin=umin, umax=umax)
        self.Kp = float(Kp)
        self.Td = float(Td)
        self.N = float(N)
        self.b = float(b)
        self.Kr = float(Kr)
        
        # Dla kompatybilności (nieużywane w PD)
        self.Ti = Ti
        self.Tt = Tt

        # Stany wewnętrzne filtra D
        self._vd = 0.0
        self._y_prev = None  # typ: Optional[float]
        # Buforowane współczynniki filtra D
        self._a_d = 0.0
        self._beta_d = 0.0
        self._d_ready = False

    # Walidacja podstawowa
        if self.dt <= 0:
            raise ValueError("dt musi być > 0")
        if self.Td < 0:
            raise ValueError("Td musi być >= 0")
        if self.N <= 0:
            raise ValueError("N musi być > 0")

    def reset(self):
        super().reset()
        self._vd = 0.0
        self._y_prev = None

    def update(self, r: float, y: float) -> float:
        # Inicjalizacja poprzedniego pomiaru przy pierwszym wywołaniu
        if self._y_prev is None:
            self._y_prev = float(y)

        # Część proporcjonalna (waga zadania b)
        e_w = self.b * r - y
        u_p = self.Kp * e_w

        # Część różniczkująca na pomiar (bez pochodnej z r, brak "kopa")
        if self.Td > 0.0:
            if not self._d_ready:
                denom = (self.Td + self.N * self.dt)
                self._a_d = self.Td / denom
                self._beta_d = (self.Kp * self.Td * self.N) / denom
                self._d_ready = True
            dy = y - self._y_prev
            self._vd = self._a_d * self._vd - self._beta_d * dy
        else:
            self._vd = 0.0

        self._y_prev = float(y)

        # Feedforward Kr*r eliminuje offset stały (PD bez I ma zawsze uchyb)
        u_ff = self.Kr * r

        u = u_p + self._vd + u_ff
        u = self._saturate(u)
        self.u = u
        return u
