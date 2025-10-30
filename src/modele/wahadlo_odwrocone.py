# src/modele/wahadlo_odwrocone.py
from __future__ import annotations
import math


class Wahadlo_odwrocone:
    """
    Simple inverted pendulum (linearized around the upright position).
    State: theta [rad], omega [rad/s]
    Output: y = theta
    Dynamics (linearized):
        theta_ddot = + (g/l) * theta + u / (m*l^2) - d * omega
    Note the PLUS sign in (g/l)*theta for the inverted (unstable) equilibrium.
    """

    def __init__(
        self,
        m: float = 1.0,
        l: float = 1.0,
        g: float = 9.81,
        d: float = 0.05,      # viscous damping
        dt: float = 0.05,
        theta0: float = 0.02, # small initial deviation from upright
        omega0: float = 0.0
    ):
        self.m = float(m)
        self.l = float(l)
        self.g = float(g)
        self.d = float(d)
        self.dt = float(dt)

        self.theta = float(theta0)
        self.omega = float(omega0)
        self.y = self.theta

    def reset(self, theta0: float = 0.02, omega0: float = 0.0) -> None:
        self.theta = float(theta0)
        self.omega = float(omega0)
        self.y = self.theta

    def step(self, u: float) -> float:
        # inverted pendulum: + (g/l)*theta
        d2theta = +(self.g / self.l) * self.theta + u / (self.m * self.l ** 2) - self.d * self.omega

        # forward Euler
        self.omega += d2theta * self.dt
        self.theta += self.omega * self.dt

        self.y = self.theta
        return self.y
