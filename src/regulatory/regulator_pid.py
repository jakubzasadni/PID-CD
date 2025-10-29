import math
import numpy as np
from src.regulatory.regulator_bazowy import RegulatorBazowy

class regulator_pid(RegulatorBazowy):
    """
    Zaawansowany regulator PID z:
    - Adaptacyjnym dostosowaniem parametrów
    - Inteligentnym anti-windupem
    - Filtracją części różniczkującej
    - Miękkim startem członu całkującego
    - Kompensacją opóźnień
    - Zabezpieczeniami numerycznymi
    """
    def __init__(self, Kp: float = 1.0, Ti: float = 30.0, Td: float = 0.0,
                 N: float = 10.0, beta: float = 1.0, dt: float = 0.05,
                 umin: float = 0.0, umax: float = 1.0):
        """
        Args:
            Kp: Wzmocnienie proporcjonalne
            Ti: Czas całkowania [s]
            Td: Czas różniczkowania [s]
            N: Częstotliwość złamania filtru D [Hz]
            beta: Współczynnik ważenia błędu (set-point weighting)
            dt: Krok czasowy [s]
            umin: Minimalne sterowanie
            umax: Maksymalne sterowanie
        """
        super().__init__(dt=dt, umin=umin, umax=umax)
        
        # Parametry główne
        self.Kp = float(Kp)
        self.Ti = max(1e-6, float(Ti))
        self.Td = max(0.0, float(Td))
        self.N = max(1.0, float(N))
        self.beta = min(1.0, max(0.0, float(beta)))
        
        # Parametry adaptacyjne
        self._Kp_base = self.Kp
        self._Ti_base = self.Ti
        self._Td_base = self.Td
        self._adaptation_rate = 0.1
        
        # Stany
        self._ui = 0.0  # człon całkujący
        self._d_filtered = 0.0  # filtrowane różniczkowanie
        self._y_prev = None
        self._e_prev = 0.0
        self._filter_alpha = self._calculate_filter_alpha()
        
        # Bufor do analizy odpowiedzi
        self._y_buffer = []
        self._max_buffer_size = 50
        
        # Parametry adaptacji
        self._min_Kp = self.Kp * 0.5
        self._max_Kp = self.Kp * 2.0
        self._min_Ti = self.Ti * 0.5
        self._max_Ti = self.Ti * 2.0
        self._response_type = "unknown"
        
        # Miękki start
        self._soft_start_count = 0
        self._soft_start_length = int(1.0 / dt)  # 1s miękkiego startu

    def _calculate_filter_alpha(self) -> float:
        """Oblicza współczynnik filtru D z uwzględnieniem szumu."""
        base_alpha = (self.dt * self.N) / (self.Td + self.dt * self.N)
        noise_factor = max(0.2, 1.0 - self.stats.noise_level * 5.0)
        return base_alpha * noise_factor

    def reset(self):
        """Resetuje stan regulatora."""
        super().reset()
        self._ui = 0.0
        self._d_filtered = 0.0
        self._y_prev = None
        self._e_prev = 0.0
        self._y_buffer.clear()
        self._soft_start_count = 0
        self._response_type = "unknown"

    def _analyze_response(self, y: float, r: float):
        """Analizuje odpowiedź układu i dostosowuje parametry."""
        self._y_buffer.append(y)
        if len(self._y_buffer) > self._max_buffer_size:
            self._y_buffer.pop(0)

        if len(self._y_buffer) >= 5:
            # Analiza odpowiedzi
            y_trend = [self._y_buffer[i] - self._y_buffer[i-1] 
                      for i in range(1, len(self._y_buffer))]
            
            # Wykrywanie oscylacji i zbieżności
            sign_changes = sum(1 for i in range(1, len(y_trend)) 
                             if y_trend[i] * y_trend[i-1] < 0)
            settling = all(abs(yt) < 0.01 for yt in y_trend[-3:])
            error = abs(y - r)
            
            # Klasyfikacja odpowiedzi
            if sign_changes > 3:
                self._response_type = "oscillatory"
            elif error > 0.1 * abs(r) and settling:
                self._response_type = "sluggish"
            elif error < 0.02 * abs(r) and settling:
                self._response_type = "good"
            
            # Adaptacja parametrów
            if self._response_type == "oscillatory":
                # Zmniejsz wzmocnienie, zwiększ Ti, zwiększ Td
                self.Kp = max(self._min_Kp, self.Kp * 0.95)
                self.Ti = min(self._max_Ti, self.Ti * 1.05)
                self.Td = min(self._Td_base * 1.5, self.Td * 1.05)
            elif self._response_type == "sluggish":
                # Zwiększ wzmocnienie, zmniejsz Ti
                self.Kp = min(self._max_Kp, self.Kp * 1.05)
                self.Ti = max(self._min_Ti, self.Ti * 0.95)

    def update(self, r: float, y: float) -> float:
        """
        Oblicza nową wartość sterowania z adaptacją i zabezpieczeniami.
        
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
        
        # Człon P z ważeniem nastawy
        if self.stats.noise_level > 0.1:
            # Zmniejsz wzmocnienie przy dużym zaszumieniu
            Kp_effective = self.Kp * (1.0 - self.stats.noise_level)
        else:
            Kp_effective = self.Kp
        
        up = Kp_effective * (self.beta * r - y)

        # Człon I z miękkim startem i adaptacją
        if self._soft_start_count < self._soft_start_length:
            # Miękki start - stopniowe włączanie całkowania
            soft_start_gain = self._soft_start_count / self._soft_start_length
            self._soft_start_count += 1
        else:
            soft_start_gain = 1.0

        # Adaptacyjne całkowanie z wagą błędu
        if self.stats.stability_index > 0.7:
            # Szybsze całkowanie gdy układ stabilny
            Ti_effective = self.Ti * 0.9
        else:
            # Wolniejsze całkowanie gdy niestabilny
            Ti_effective = self.Ti * 1.2

        ui_delta = Kp_effective * (self.dt / Ti_effective) * e * soft_start_gain
        ui_candidate = self._ui + ui_delta

        # Człon D z filtracją i zabezpieczeniami
        if self._y_prev is None or self.Td == 0.0:
            ud = 0.0
        else:
            # Różniczkowanie po pomiarze (unikanie derivative kick)
            dy = y - self._y_prev
            
            # Ograniczenie maksymalnej szybkości zmian
            max_dy = 10.0 * abs(r - self._y_prev)  # max 1000% zmiana/dt
            dy_limited = np.clip(dy, -max_dy, max_dy)
            
            # Filtracja różniczkowania
            dy_dt = -dy_limited / self.dt
            self._filter_alpha = self._calculate_filter_alpha()
            self._d_filtered = self._lpf_step(self._d_filtered, dy_dt, self._filter_alpha)
            ud = Kp_effective * self.Td * self._d_filtered

        # Składanie sterowania
        u_raw = up + ui_candidate + ud
        u_limited = self._rate_limit(u_raw)
        u_sat = self._saturate(u_limited)

        # Zaawansowany anti-windup
        if abs(u_sat - u_raw) > 1e-6:  # jest saturacja
            if (u_raw > self.umax and e > 0) or (u_raw < self.umin and e < 0):
                # Nie aktualizuj całki gdy saturacja pogarsza sytuację
                pass
            else:
                # Ograniczone całkowanie z korekcją back-calculation
                windup_correction = 0.1 * (u_sat - u_raw) / (abs(u_raw) + 1e-6)
                self._ui = ui_candidate + windup_correction
        else:
            # Normalna aktualizacja całki
            self._ui = ui_candidate

        # Aktualizacja stanów
        self._y_prev = y
        self._e_prev = e
        self.u_prev = u_sat
        
        # Analiza odpowiedzi i adaptacja
        self._analyze_response(y, r)
        
        # Aktualizacja statystyk
        self._update_stats(e, u_raw, u_sat)
        
        return u_sat

    def _rate_limit(self, u_new: float) -> float:
        """Ogranicza szybkość zmian sterowania."""
        if not hasattr(self, 'u_prev'):
            return u_new
        max_change = abs(self.umax - self.umin) * 0.1 * self.dt  # max 10% zakresu/s
        delta_u = np.clip(u_new - self.u_prev, -max_change, max_change)
        return self.u_prev + delta_u

    def get_recommended_params(self) -> dict:
        """Zwraca rekomendowane parametry na podstawie historii."""
        if len(self._y_buffer) < self._max_buffer_size:
            return {
                'Kp': self._Kp_base,
                'Ti': self._Ti_base,
                'Td': self._Td_base
            }

        # Analiza odpowiedzi
        oscillations = sum(1 for i in range(1, len(self._y_buffer)-1)
                         if (self._y_buffer[i] - self._y_buffer[i-1]) *
                            (self._y_buffer[i+1] - self._y_buffer[i]) < 0)
        
        settling_error = np.std(self._y_buffer[-10:])
        
        if oscillations > 5:  # Zbyt oscylacyjna
            return {
                'Kp': self.Kp * 0.8,
                'Ti': self.Ti * 1.2,
                'Td': self.Td * 1.2
            }
        elif settling_error > 0.1:  # Zbyt wolna
            return {
                'Kp': self.Kp * 1.2,
                'Ti': self.Ti * 0.8,
                'Td': self.Td * 0.9
            }
        else:  # Dobra odpowiedź
            return {
                'Kp': self.Kp,
                'Ti': self.Ti,
                'Td': self.Td
            }
