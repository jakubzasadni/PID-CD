# src/pid.py
# PID with filtered D and anti-windup (back-calculation)

from dataclasses import dataclass

@dataclass
class PID:
    kp: float
    ti: float           # integral time [s], use >0 for PI/PID; large for P-only
    td: float           # derivative time [s]
    dt: float
    n: float = 10.0     # derivative filter coefficient
    umin: float = 0.0
    umax: float = 1.0
    kaw: float = 1.0    # anti-windup back-calculation gain

    # internal states
    i_state: float = 0.0
    d_state: float = 0.0
    u_last: float = 0.0
    e_last: float = 0.0

    def reset(self):
        self.i_state = 0.0
        self.d_state = 0.0
        self.u_last = 0.0
        self.e_last = 0.0

    def update(self, r: float, y: float) -> float:
        e = r - y

        # Proportional
        up = self.kp * e

        # Integral (trapezoidal)
        if self.ti > 0.0:
            ki = self.kp / self.ti
        else:
            ki = 0.0
        i_new = self.i_state + ki * e * self.dt

        # Derivative with first-order filter: D(s) = (Td*s)/(1 + Td/N*s)
        # Discrete form (Tustin-like)
        if self.td > 0.0:
            alpha = self.td / (self.td + self.n * self.dt)
            d_new = alpha * self.d_state + (1 - alpha) * (e - self.e_last) * self.n
        else:
            d_new = 0.0

        u_unsat = up + i_new + self.kp * self.td * d_new

        # Saturation
        u = max(self.umin, min(self.umax, u_unsat))

        # Anti-windup (back-calculation)
        aw = self.kaw * (u - u_unsat)
        self.i_state = i_new + aw * self.dt

        # Update states
        self.d_state = d_new
        self.e_last = e
        self.u_last = u
        return u
