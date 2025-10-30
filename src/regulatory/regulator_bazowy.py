"""
RegulatorBazowy
----------------
Minimalna, ujednolicona baza dla regulatorów używana w projekcie.

Gwarantuje:
- spójną inicjalizację (dt, umin, umax)
- metody pomocnicze: _saturate, _rate_limit
- walidację parametrów (validate_params)
- podstawową diagnostykę (get_diagnostics)
"""

from typing import Dict, Optional


class RegulatorBazowy:
    def __init__(self, dt: float = 0.05, umin: Optional[float] = None, umax: Optional[float] = None):
        """Inicjalizacja bazowa regulatora.

        Args:
            dt: krok czasowy [s]
            umin: minimalne sterowanie (None -> brak ograniczenia)
            umax: maksymalne sterowanie (None -> brak ograniczenia)
        """
        if dt <= 0:
            raise ValueError("dt musi być większe od 0")
        self.dt = float(dt)
        self.u = 0.0
        self.u_prev = 0.0
        self.umin = umin
        self.umax = umax

        # prosta diagnostyka
        self._total_steps = 0
        self._saturated_steps = 0

    def reset(self) -> None:
        """Resetuje stan regulatora."""
        self.u = 0.0
        self.u_prev = 0.0
        self._total_steps = 0
        self._saturated_steps = 0

    def validate_params(self) -> None:
        """Walidacja podstawowych parametrów (może być rozszerzona w klasach pochodnych)."""
        if self.dt <= 0:
            raise ValueError("dt must be > 0")
        if (self.umin is not None) and (self.umax is not None) and (self.umin >= self.umax):
            raise ValueError("umin must be < umax")

    def _saturate(self, u: float) -> float:
        """Zwraca sygnał ograniczony do [umin, umax] jeśli wartości te są zdefiniowane."""
        u_sat = u
        if self.umin is not None:
            u_sat = max(self.umin, u_sat)
        if self.umax is not None:
            u_sat = min(self.umax, u_sat)
        # aktualizacja diagnostyki
        self._total_steps += 1
        if abs(u_sat - u) > 1e-12:
            self._saturated_steps += 1
        return u_sat

    def _rate_limit(self, u_new: float, max_rate: Optional[float] = None) -> float:
        """Ogranicza szybkość zmian sygnału sterującego.

        Args:
            u_new: propozycja nowego sygnału
            max_rate: maksymalna szybkość zmian (jednostka: jednostka_u / s). Jeśli None -> brak limitu.
        """
        if max_rate is None or max_rate == float("inf"):
            return u_new
        max_change = abs(float(max_rate)) * self.dt
        delta = u_new - self.u_prev
        if delta > max_change:
            return self.u_prev + max_change
        if delta < -max_change:
            return self.u_prev - max_change
        return u_new

    def get_diagnostics(self) -> Dict[str, float]:
        """Zwraca podstawowe statystyki regulatora (liczba kroków i udział saturacji)."""
        total = max(1, self._total_steps)
        return {
            "total_steps": self._total_steps,
            "saturation_ratio": float(self._saturated_steps) / total,
        }

    def update(self, r: float, y: float) -> float:
        raise NotImplementedError("Metoda update() musi zostać zaimplementowana w klasie pochodnej.")
