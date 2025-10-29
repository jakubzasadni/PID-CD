from math import isfinite
from src.regulatory.regulator_bazowy import RegulatorBazowy

class regulator_pd(RegulatorBazowy):
    """
    PD z pochodną od pomiaru (brak derivative kick) + filtr 1-rzędu na D.
    U = Kp * e  +  Kp*Td * d_filt, gdzie d_filt ~ -(dy/dt) po odfiltrowaniu.
    Parametry:
      Kp (float)
      Td (float) – czas różniczkowania [s]
      N  (float) – „ostrość” filtru (większe N -> szybsza pochodna), domyślnie 10
      umin/umax – opcjonalne ograniczenia wyjścia
    """

    def __init__(self, Kp: float = 1.0, Td: float = 0.0, N: float = 10.0, dt: float = 0.05,
                 umin: float = float("-inf"), umax: float = float("inf")):
        super().__init__(dt=dt, umin=umin, umax=umax)
        self.Kp = float(Kp)
        self.Td = max(0.0, float(Td))
        self.N  = max(1.0, float(N))   # N >= 1
        # stan filtru pochodnej i poprzedni pomiar
        self._d_filt = 0.0
        self._y_prev = None
        # stała filtru: tau_d = Td/N  =>  alpha = dt / (tau_d + dt)
        self._alpha = 0.0 if self.Td == 0.0 else (self.dt * self.N) / (self.Td + self.dt * self.N)

    def reset(self):
        super().reset()
        self._d_filt = 0.0
        self._y_prev = None

    def update(self, r: float, y: float) -> float:
        e = (r - y)

        # --- pochodna od pomiaru, żeby uniknąć derivative kick ---
        if self._y_prev is None or self.Td == 0.0:
            dy_dt = 0.0
        else:
            dy_dt = (y - self._y_prev) / self.dt

        raw_d = -dy_dt  # minus bo D od pomiaru
        self._d_filt = self._lpf_step(self._d_filt, raw_d, self._alpha)

        u_unsat = self.Kp * e + self.Kp * self.Td * self._d_filt
        u_sat   = self._saturate(u_unsat)

        self._y_prev = y
        self.u_prev = u_sat
        return u_sat
