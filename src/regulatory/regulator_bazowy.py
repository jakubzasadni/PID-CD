"""
Klasa bazowa dla regulatorów.
Daje: dt, saturację, prosty low-pass i reset stanu.
"""

import math

class RegulatorBazowy:
    def __init__(self, dt: float = 0.05, umin: float = -math.inf, umax: float = math.inf):
        self.dt = float(dt)
        self.umin = float(umin)
        self.umax = float(umax)
        self.u_prev = 0.0

    def reset(self):
        self.u_prev = 0.0

    # --- pomocnicze ---
    def _saturate(self, u: float) -> float:
        if u > self.umax: 
            return self.umax
        if u < self.umin: 
            return self.umin
        return u

    def _lpf_step(self, prev: float, now: float, alpha: float) -> float:
        """y(k) = y(k-1) + alpha * (now - y(k-1)); alpha ∈ [0,1]"""
        if alpha <= 0.0: 
            return prev
        if alpha >= 1.0: 
            return now
        return prev + alpha * (now - prev)
