# src/modele/wahadlo_odwrocone.py
from src.modele.model_bazowy import ModelBazowy
import math

class Wahadlo_odwrocone(ModelBazowy):
    """
    Model uproszczonego wahadła odwróconego.
    """
    def __init__(self, m=0.2, l=0.5, g=9.81, dt=0.01):
        super().__init__(dt)
        self.m = m
        self.l = l
        self.g = g
        self.theta = 0.05  # początkowe odchylenie [rad]
        self.omega = 0.0

    def step(self, u):
        d2theta = (self.g / self.l) * math.sin(self.theta) + u / (self.m * self.l ** 2)
        self.omega += d2theta * self.dt
        self.theta += self.omega * self.dt
        self.y = self.theta
        return self.y
