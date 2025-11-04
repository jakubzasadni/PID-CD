# src/regulatory/regulator_pi.py
from src.regulatory.regulator_bazowy import RegulatorBazowy


class Regulator_PI(RegulatorBazowy):
    """
    Regulator PI (proporcjonalno-całkujący):
    - Proporcjonalne na ważone zadanie: u_P = Kp * (b*r - y)
    - Całkowanie błędu z anti-windup (back-calculation, współczynnik Tt)
    - Feedforward Kr*r dla szybkiej reakcji początkowej (domyślnie Kr=1.0)

    Parametry:
    - Kp: wzmocnienie proporcjonalne (domyślnie 1.0)
    - Ti: stała całkowania w sekundach (domyślnie 10.0)
    - Tt: stała anti-windup (domyślnie Tt=Ti, back-calculation 1:1)
    - b:  waga wartości zadanej w członie P (domyślnie 1.0)
    - Kr: wzmocnienie feedforward (domyślnie 1.0) — zapewnia szybki start
    - dt: krok próbkowania (domyślnie 0.05)
    - umin, umax: ograniczenia sygnału (domyślnie None — brak saturacji)
    
    Nieużywane w PI (dla kompatybilności z PD/PID):
    - Td, N (ignorowane)
    """

    def __init__(
        self,
        Kp: float = 1.0,
        Ti: float = 10.0,
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
        self.Ti = float(Ti)
        self.b = float(b)
        # Kr=1.0 dla porównywalności z P/PD (zapewnia szybki start)
        self.Kr = float(Kr)
        
        # Anti-windup: Tt domyślnie = Ti (standardowa back-calculation)
        self.Tt = float(Tt) if Tt is not None else self.Ti
        
        # Dla kompatybilności (nieużywane w PI)
        self.Td = Td
        self.N = N

        # Aliasy dla starego API
        self.kp = self.Kp
        self.ti = self.Ti

        # Stan wewnętrzny
        self._ui = 0.0  # suma całkująca

        # Walidacja
        if self.dt <= 0:
            raise ValueError("dt musi być > 0")
        if self.Ti <= 0:
            raise ValueError("Ti musi być > 0")
        if self.Tt <= 0:
            raise ValueError("Tt musi być > 0")

    def reset(self):
        super().reset()
        self._ui = 0.0

    def update(self, r: float, y: float) -> float:
        # Walidacja czasu próbkowania
        if self.dt <= 0:
            raise ValueError("dt musi być > 0")
        # Część proporcjonalna (waga b)
        e_w = self.b * r - y
        u_p = self.Kp * e_w

        # Błąd pełny (dla całkowania)
        e = r - y

        # Część całkująca przed saturacją
        u_i_raw = self._ui
        u_raw = u_p + u_i_raw + self.Kr * r

        # Saturacja
        u = self._saturate(u_raw)

        # Anti-windup: back-calculation (Åström-Hägglund)
        # Jeśli u != u_raw, to znaczy że nastąpiła saturacja:
        # korygujemy ui o błąd (u - u_raw) / Tt
        e_sat = u - u_raw
        self._ui += (self.Kp / self.Ti) * e * self.dt + (1.0 / self.Tt) * e_sat * self.dt

        self.u = u
        return u
