import math
import numpy as np
from src.regulatory.regulator_bazowy import RegulatorBazowy

class regulator_pd(RegulatorBazowy):
    """
    Zaawansowany regulator PD z:
    - Filtracją części różniczkującej
    - Adaptacyjnym skalowaniem wzmocnienia
    - Kompensacją opóźnień
    - Zabezpieczeniem przed derivative kick
    - Miękkim przejściem sterowania
    """
    def __init__(self, Kp: float = 1.0, Td: float = 0.0, Kr: float = 1.0, 
                 dt: float = 0.05, umin=None, umax=None, N: float = 10.0):
        """
        Args:
            Kp: Wzmocnienie proporcjonalne
            Td: Czas różniczkowania [s]
            Kr: Współczynnik skalowania wartości zadanej
            dt: Krok czasowy [s]
            umin: Minimalne sterowanie
            umax: Maksymalne sterowanie
            N: Częstotliwość złamania filtru D [Hz]
        """
        super().__init__(dt=dt, umin=umin, umax=umax)
        self.Kp = float(Kp)
        self.Td = float(Td)
        self.Kr = float(Kr)
        self.N = float(N)
        
        # Parametry adaptacyjne
        self._Kp_base = self.Kp
        self._Td_base = self.Td
        self._adaptation_rate = 0.1
        
        # Stany
        self._e_prev = 0.0
        self._y_prev = None
        self._d_filtered = 0.0
        self._filter_alpha = self._calculate_filter_alpha()
        
        # Bufor pomiarów do analizy trendu
        self._y_buffer = []
        self._max_buffer_size = 20
        
        # Parametry adaptacji
        self._min_Kp = self.Kp * 0.5
        self._max_Kp = self.Kp * 2.0
        self._response_type = "unknown"  # "underdamped", "overdamped", "unknown"

    def _calculate_filter_alpha(self) -> float:
        """Oblicza współczynnik filtru D z uwzględnieniem poziomu szumu."""
        base_alpha = (self.dt * self.N) / (self.Td + self.dt * self.N)
        noise_factor = max(0.2, 1.0 - self.stats.noise_level * 5.0)
        return base_alpha * noise_factor

    def reset(self):
        """Resetuje stan regulatora."""
        super().reset()
        self._e_prev = 0.0
        self._y_prev = None
        self._d_filtered = 0.0
        self._y_buffer.clear()
        self._response_type = "unknown"

    def _analyze_response(self, y: float, r: float):
        """Analizuje odpowiedź układu i dostosowuje parametry."""
        self._y_buffer.append(y)
        if len(self._y_buffer) > self._max_buffer_size:
            self._y_buffer.pop(0)

        if len(self._y_buffer) >= 3:
            # Wykrywanie przeregulowania i niedoregulowania
            y_trend = [self._y_buffer[i] - self._y_buffer[i-1] 
                      for i in range(1, len(self._y_buffer))]
            sign_changes = sum(1 for i in range(1, len(y_trend)) 
                             if y_trend[i] * y_trend[i-1] < 0)
            
            if sign_changes > 2:
                self._response_type = "underdamped"
            elif abs(y - r) > 0.1 * abs(r) and all(abs(yt) < 1e-3 for yt in y_trend[-3:]):
                self._response_type = "overdamped"
            
            # Adaptacja parametrów
            if self._response_type == "underdamped":
                # Zmniejsz wzmocnienie i zwiększ tłumienie
                self.Kp = max(self._min_Kp, self.Kp * 0.95)
                self.Td = min(self._Td_base * 1.5, self.Td * 1.05)
            elif self._response_type == "overdamped":
                # Zwiększ wzmocnienie i zmniejsz tłumienie
                self.Kp = min(self._max_Kp, self.Kp * 1.05)
                self.Td = max(self._Td_base * 0.7, self.Td * 0.95)

    def update(self, r: float, y: float) -> float:
        """
        Oblicza nową wartość sterowania z adaptacją i filtracją.
        
        Args:
            r: Wartość zadana
            y: Wartość zmierzona
        Returns:
            Nowa wartość sterowania
        """
        # Analiza jakości sygnału
        self._estimate_signal_quality(y, r)
        
        # Podstawowy błąd
        e = r - y
        
        # Człon P z adaptacyjnym wzmocnieniem
        if self.stats.noise_level > 0.1:
            # Zmniejsz wzmocnienie przy dużym zaszumieniu
            Kp_effective = self.Kp * (1.0 - self.stats.noise_level)
        else:
            Kp_effective = self.Kp
        
        up = Kp_effective * e

        # Człon D z filtracją i zabezpieczeniami
        if self._y_prev is None:
            ud = 0.0
        else:
            # Różniczkowanie po pomiarze (unikanie derivative kick)
            dy = y - self._y_prev
            
            # Ograniczenie maksymalnej szybkości zmian
            max_dy = 10.0 * abs(r - self._y_prev)  # max 1000% zmiana/dt
            dy_limited = np.clip(dy, -max_dy, max_dy)
            
            # Filtracja różniczkowania
            dy_dt = -dy_limited / self.dt  # minus bo różniczkujemy po -y
            self._filter_alpha = self._calculate_filter_alpha()
            self._d_filtered = self._lpf_step(self._d_filtered, dy_dt, self._filter_alpha)
            ud = Kp_effective * self.Td * self._d_filtered

        # Człon feed-forward
        uff = self.Kr * r

        # Składanie sterowania z miękkim przejściem
        u_raw = uff + up + ud
        u_limited = self._rate_limit(u_raw)  # ograniczenie szybkości zmian
        u = self._saturate(u_limited)  # saturacja z miękkim przejściem
        
        # Aktualizacja stanów
        self._y_prev = y
        self._e_prev = e
        self.u_prev = u
        
        # Analiza odpowiedzi i adaptacja
        self._analyze_response(y, r)
        
        # Aktualizacja statystyk
        self._update_stats(e, u_raw, u)
        
        return u

    def _rate_limit(self, u_new: float) -> float:
        """Ogranicza szybkość zmian sterowania."""
        if not hasattr(self, 'u_prev'):
            return u_new
        max_change = abs(self.umax - self.umin) * 0.1 * self.dt  # max 10% zakresu/s
        delta_u = np.clip(u_new - self.u_prev, -max_change, max_change)
        return self.u_prev + delta_u
