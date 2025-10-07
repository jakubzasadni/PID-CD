# src/regulatory/regulator_dwupolozeniowy.py
from src.regulatory.regulator_bazowy import RegulatorBazowy

class Regulator_dwupolozeniowy(RegulatorBazowy):
    """
    Regulator dwupołożeniowy (ON/OFF).
    """
    def __init__(self, prog=0.05, dt=0.05):
        super().__init__(dt)
        self.prog = prog

    def update(self, r, y):
        e = r - y
        self.u = 1.0 if e > self.prog else 0.0
        return self.u
