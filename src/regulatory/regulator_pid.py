# src/regulatory/regulator_pid.py
from src.regulatory.regulator_bazowy import RegulatorBazowy


class Regulator_PID(RegulatorBazowy):
    """
    Regulator PID (proporcjonalno-całkująco-różniczkujący):
    - Proporcjonalne na ważone zadanie: u_P = Kp * (b*r - y)
    - Całkowanie błędu z anti-windup (back-calculation, współczynnik Tt)
    - Różniczkujące na pomiar (filtrowane, współczynnik N)
    - Feedforward Kr*r dla szybkiej reakcji początkowej (domyślnie Kr=1.0)

    Parametry:
    - Kp: wzmocnienie proporcjonalne (domyślnie 1.0)
    - Ti: stała całkowania w sekundach (domyślnie 10.0)
    - Td: stała różniczkowania w sekundach (domyślnie 0.0)
    - N:  współczynnik filtra pochodnej (domyślnie 10.0)
    - Tt: stała anti-windup (domyślnie Tt=Ti, back-calculation 1:1)
    - b:  waga wartości zadanej w członie P (domyślnie 1.0)
    - Kr: wzmocnienie feedforward (domyślnie 1.0) — zapewnia szybki start
    - dt: krok próbkowania (domyślnie 0.05)
    - umin, umax: ograniczenia sygnału (domyślnie 0.0, 1.0)
    """

    def __init__(
        self,
        Kp: float = 1.0,
        Ti: float = 10.0,
        Td: float = 0.0,
        dt: float = 0.05,
        umin: float = 0.0,
        umax: float = 1.0,
        b: float = 1.0,
        Kr: float = 1.0,
        N: float = 10.0,
        Tt: float | None = None,
    ):
        super().__init__(dt=dt, umin=umin, umax=umax)
        self.Kp = float(Kp)
        self.Ti = float(Ti)
        self.Td = float(Td)
        self.N = float(N)
        self.b = float(b)
        self.Kr = float(Kr)
        
        # Anti-windup: Tt domyślnie = Ti
        self.Tt = float(Tt) if Tt is not None else self.Ti

        # Aliasy dla starego API
        self.kp = self.Kp
        self.ti = self.Ti
        self.td = self.Td
        self.n = self.N
        self.kaw = 1.0  # stary parametr, teraz używamy Tt

        # Stany wewnętrzne
        self._ui = 0.0
        self._vd = 0.0
        self._y_prev = None

        # Walidacja
        if self.Ti <= 0:
            raise ValueError("Ti musi być > 0")
        if self.Td < 0:
            raise ValueError("Td musi być >= 0")
        if self.N <= 0:
            raise ValueError("N musi być > 0")
        if self.Tt <= 0:
            raise ValueError("Tt musi być > 0")

    def reset(self):
        super().reset()
        self._ui = 0.0
        self._vd = 0.0
        self._y_prev = None

    def update(self, r: float, y: float) -> float:
        # Inicjalizacja poprzedniego pomiaru
        if self._y_prev is None:
            self._y_prev = float(y)

        # Część proporcjonalna (waga b)
        e_w = self.b * r - y
        u_p = self.Kp * e_w

        # Błąd pełny (dla całkowania)
        e = r - y

        # Część różniczkująca na pomiar (filtrowana)
        if self.Td > 0.0:
            a = self.Td / (self.Td + self.N * self.dt)
            beta = (self.Kp * self.Td * self.N) / (self.Td + self.N * self.dt)
            dy = y - self._y_prev
            self._vd = a * self._vd - beta * dy
        else:
            self._vd = 0.0

        self._y_prev = float(y)

        # Sygnał przed saturacją
        u_raw = u_p + self._ui + self._vd + self.Kr * r

        # Saturacja
        u = self._saturate(u_raw)

        # Anti-windup: back-calculation
        e_sat = u - u_raw
        self._ui += (self.Kp / self.Ti) * e * self.dt + (1.0 / self.Tt) * e_sat * self.dt

        self.u = u
        return u
