# src/modele/wahadlo_odwrocone.py
from src.modele.model_bazowy import ModelBazowy
import math

class Wahadlo_odwrocone(ModelBazowy):
    """
    Uproszczony model wahadła odwróconego (liniowy w pobliżu pionu).
    θ = kąt wychylenia [rad]
    ω = prędkość kątowa [rad/s]
    u = moment sterujący (siła stabilizująca)
    """
    def __init__(self, m=0.2, l=0.5, g=9.81, d=0.3, dt=0.01):
        super().__init__(dt)
        self.m = m      # masa [kg]
        self.l = l      # długość wahadła [m]
        self.g = g      # przysp. grawitacyjne [m/s^2]
        self.d = d      # współczynnik tłumienia
        self.theta = 0.05   # początkowy kąt od pionu [rad]
        self.omega = 0.0
        self.y = self.theta # wyjście = kąt

    def step(self, u):
        # Równanie ruchu wahadła odwróconego (liniowe)
        d2theta = -(self.g / self.l) * self.theta + u / (self.m * self.l ** 2) - self.d * self.omega

        # Integracja numeryczna (Euler)
        self.omega += d2theta * self.dt
        self.theta += self.omega * self.dt
        self.y = self.theta
        return self.y
