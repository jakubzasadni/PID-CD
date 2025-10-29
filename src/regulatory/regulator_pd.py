class regulator_pd(RegulatorBazowy):
    """
    PD z pochodną od pomiaru + filtr 1-rzędu + P z ważeniem nastawy (beta).
    """
    def __init__(self, Kp: float = 2.0, Td: float = 0.8, N: float = 5.0, beta: float = 0.8,
                 dt: float = 0.05, umin: float = float("-inf"), umax: float = float("inf")):
        super().__init__(dt=dt, umin=umin, umax=umax)
        self.Kp   = float(Kp)
        self.Td   = max(0.0, float(Td))
        self.N    = max(1.0, float(N))
        self.beta = min(1.0, max(0.0, float(beta)))
        self._d_filt = 0.0
        self._y_prev = None
        self._alpha = 0.0 if self.Td == 0.0 else (self.dt * self.N) / (self.Td + self.dt * self.N)

    def update(self, r: float, y: float) -> float:
        # P z ważeniem nastawy
        up = self.Kp * (self.beta * r - y)

        # D od pomiaru + filtr
        if self._y_prev is None or self.Td == 0.0:
            dy_dt = 0.0
        else:
            dy_dt = (y - self._y_prev) / self.dt
        raw_d = -dy_dt
        self._d_filt = self._lpf_step(self._d_filt, raw_d, self._alpha)
        ud = self.Kp * self.Td * self._d_filt

        u = self._saturate(up + ud)
        self._y_prev = y
        self.u_prev = u
        return u
