# src/modele/wahadlo_odwrocone.py
from src.modele.model_bazowy import ModelBazowy
import math

class Wahadlo_odwrocone(ModelBazowy):
    def __init__(self, m=0.2, l=0.5, g=9.81, d=1.2, dt=0.01):
        super().__init__(dt)
        self.m = m
        self.l = l
        self.g = g
        self.d = d
        self.theta = 0.02   # mniejsze odchylenie startowe
        self.omega = 0.0
        self.y = self.theta

    def step(self, u):
        d2theta = -(self.g / self.l) * self.theta + u / (self.m * self.l ** 2) - self.d * self.omega
        self.omega += d2theta * self.dt
        self.theta += self.omega * self.dt
        # opcjonalny clamp liniowy:
        # self.theta = max(min(self.theta, 0.3), -0.3)
        self.y = self.theta
        return self.y

