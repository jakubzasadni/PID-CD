from src.regulatory.regulator_bazowy import RegulatorBazowy


class regulator_pd(RegulatorBazowy):
    """
    Ulepszony regulator PD:
    - Proporcjonalne na ważone zadanie: u_P = Kp * (b*r - y)
    - Różniczkujące na pomiar (bez "derivative kick"), filtrowane (współczynnik N):
        v_d[k] = a * v_d[k-1] - beta * (y[k] - y[k-1])
        a    = Td / (Td + N*dt)
        beta = Kp * Td * N / (Td + N*dt)
    - Feedforward Kr*r dla eliminacji offsetu stałego (domyślnie Kr=1.0)

    Parametry:
    - Kp: wzmocnienie proporcjonalne
    - Td: stała różniczkowania (s)
    - N:  współczynnik filtra (domyślnie 10.0)
    - b:  waga wartości zadanej w członie P (domyślnie 1.0)
    - Kr: wzmocnienie feedforward (domyślnie 1.0) — dodaje u_ff = Kr*r do sygnału sterującego,
          aby wyrównać offset; dla idealnego modelu Kr ≈ 1/K_proc
    - dt, umin, umax: z klasy bazowej
    """

    def __init__(
        self,
        Kp: float = 1.0,
        Td: float = 0.0,
        Kr: float = 1.0,
        dt: float = 0.05,
        umin=None,
        umax=None,
        N: float = 10.0,
        b: float = 1.0,
    ):
        super().__init__(dt=dt, umin=umin, umax=umax)
        self.Kp = float(Kp)
        self.Td = float(Td)
        self.N = float(N)
        self.b = float(b)
        self.Kr = float(Kr)

        # Stany wewnętrzne filtra D
        self._vd = 0.0
        self._y_prev = None  # typ: Optional[float]

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
            a = self.Td / (self.Td + self.N * self.dt)
            beta = (self.Kp * self.Td * self.N) / (self.Td + self.N * self.dt)
            dy = y - self._y_prev
            self._vd = a * self._vd - beta * dy
        else:
            self._vd = 0.0

        self._y_prev = float(y)

        # Feedforward Kr*r eliminuje offset stały (PD bez I ma zawsze uchyb)
        u_ff = self.Kr * r

        u = u_p + self._vd + u_ff
        u = self._saturate(u)
        self.u = u
        return u
