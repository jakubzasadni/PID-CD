# src/regulatory/regulator_pi.py
from src.regulatory.regulator_bazowy import RegulatorBazowy


class Regulator_PI(RegulatorBazowy):
    """
    Ulepszony regulator PI:
    - Proporcjonalne na ważone zadanie: u_P = Kp * (b*r - y)
    - Całkowanie błędu z anti-windup (back-calculation, współczynnik Tt)
    - Opcjonalny feedforward Kr*r dla szybszej reakcji (domyślnie Kr=0.0, bo I eliminuje offset)

    Parametry:
    - Kp (kp): wzmocnienie proporcjonalne
    - Ti (ti): stała całkowania (s)
    - Tt: stała anti-windup (domyślnie Tt = Ti, czyli back-calculation 1:1)
    - b:  waga wartości zadanej w członie P (domyślnie 1.0)
    - Kr: wzmocnienie feedforward (domyślnie 0.0) — dla PI rzadko potrzebne, bo I eliminuje offset
    - dt, umin, umax: z klasy bazowej
    """

    def __init__(
        self,
        kp: float = 1.0,
        ti: float = 30.0,
        umin: float = 0.0,
        umax: float = 1.0,
        dt: float = 0.05,
        Tt: float | None = None,
        b: float = 1.0,
        Kr: float = 0.0,
    ):
        super().__init__(dt=dt, umin=umin, umax=umax)
        self.Kp = float(kp)  # alias dla kompatybilności
        self.kp = self.Kp
        self.Ti = float(ti)
        self.ti = self.Ti
        self.b = float(b)
        self.Kr = float(Kr)
        
        # Anti-windup: Tt domyślnie = Ti (standardowa back-calculation)
        self.Tt = float(Tt) if Tt is not None else self.Ti

        # Stan wewnętrzny
        self._ui = 0.0  # suma całkująca

        # Walidacja
        if self.Ti <= 0:
            raise ValueError("Ti musi być > 0")
        if self.Tt <= 0:
            raise ValueError("Tt musi być > 0")

    def reset(self):
        super().reset()
        self._ui = 0.0

    def update(self, r: float, y: float) -> float:
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
