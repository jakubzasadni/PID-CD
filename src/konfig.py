"""
Moduł do wczytywania i zarządzania konfiguracją systemu strojenia.
Zapewnia fallback na wartości domyślne jeśli config.yaml nie istnieje.
"""

import os
import yaml
import logging
from pathlib import Path
from typing import Dict, Any, List, Tuple

# Domyślna konfiguracja jako fallback
DOMYSLNA_KONFIGURACJA = {
    'zakresy_parametrow': {
        'default': {
            'Kp': [0.1, 30.0],
            'Ti': [2.0, 50.0],
            'Td': [0.1, 15.0]
        }
    },
    'wagi_kary': {
        'przeregulowanie': 0.5,
        'czas_ustalania': 0.01,
        'sterowanie_stale': 1000
    },
    'gestosc_siatki': {
        'regulator_p': {'Kp': 25},
        'regulator_pi': {'Kp': 20, 'Ti': 15},
        'regulator_pd': {'Kp': 20, 'Td': 15},
        'regulator_pid': {'Kp': 15, 'Ti': 12, 'Td': 12}
    },
    'adaptacyjne_przeszukiwanie': {
        'enabled': True,
        'faza_gruba': {'gestosc_mnoznik': 0.3},
        'faza_dokladna': {'margines_procent': 0.2, 'gestosc_mnoznik': 1.5}
    },
    'optymalizacja': {
        'punkty_startowe': {
            'uzyj_ziegler_nichols': True,
            'liczba_multi_start': 3,
            'metoda': 'L-BFGS-B',
            'maxiter': 500
        }
    },
    'rownolegle': {
        'enabled': True,
        'n_jobs': -1
    },
    'logowanie': {
        'poziom': 'INFO',
        'plik_log': 'wyniki/strojenie.log',
        'loguj_niepowodzenia': True
    },
    'walidacja': {
        'scenariusze': [
            {'nazwa': 'Skok wartości zadanej (mały)', 'typ': 'setpoint_step', 'wielkosc': 5.0, 'czas_skoku': 10.0},
            {'nazwa': 'Skok wartości zadanej (duży)', 'typ': 'setpoint_step', 'wielkosc': 15.0, 'czas_skoku': 10.0},
        ],
        'progi_akceptacji': {
            'IAE_max': 18.0,
            'przeregulowanie_max': 45.0,
            'czas_ustalania_max': 70.0
        }
    },
    'raportowanie': {
        'generuj_raport_porownawczy': True,
        'format_wykresow': 'png',
        'dpi': 150,
        'pokaz_czas_obliczen': True
    }
}

class Konfiguracja:
    """Klasa do zarządzania konfiguracją systemu."""
    
    def __init__(self, sciezka_config: str = None):
        """
        Inicjalizuje konfigurację.
        
        Args:
            sciezka_config: Ścieżka do pliku config.yaml. Jeśli None, szuka w src/config.yaml
        """
        self.config = DOMYSLNA_KONFIGURACJA.copy()
        
        if sciezka_config is None:
            # Szukaj config.yaml w katalogu src
            katalog_src = Path(__file__).parent
            sciezka_config = katalog_src / 'config.yaml'
        
        if os.path.exists(sciezka_config):
            try:
                with open(sciezka_config, 'r', encoding='utf-8') as f:
                    config_z_pliku = yaml.safe_load(f)
                    if config_z_pliku:
                        self._aktualizuj_rekurencyjnie(self.config, config_z_pliku)
                logging.info(f"Wczytano konfigurację z pliku: {sciezka_config}")
            except Exception as e:
                logging.warning(f"Nie udało się wczytać konfiguracji z {sciezka_config}: {e}. Używam domyślnej.")
        else:
            logging.warning(f"Plik konfiguracyjny {sciezka_config} nie istnieje. Używam domyślnej konfiguracji.")
    
    def _aktualizuj_rekurencyjnie(self, dict_bazowy: dict, dict_nadpisujacy: dict):
        """Rekurencyjnie aktualizuje słownik bazowy wartościami z nadpisującego."""
        for klucz, wartosc in dict_nadpisujacy.items():
            if isinstance(wartosc, dict) and klucz in dict_bazowy and isinstance(dict_bazowy[klucz], dict):
                self._aktualizuj_rekurencyjnie(dict_bazowy[klucz], wartosc)
            else:
                dict_bazowy[klucz] = wartosc
    
    def pobierz_zakresy(self, regulator: str, model: str) -> Dict[str, Tuple[float, float]]:
        """
        Pobiera zakresy parametrów dla danego regulatora i modelu.
        
        Args:
            regulator: Nazwa regulatora (np. 'regulator_pid')
            model: Nazwa modelu (np. 'zbiornik_1rz')
        
        Returns:
            Słownik z zakresami: {'Kp': (min, max), 'Ti': (min, max), 'Td': (min, max)}
        """
        zakresy_config = self.config['zakresy_parametrow']
        
        # Sprawdź czy są specyficzne zakresy dla modelu
        if model in zakresy_config:
            zakresy = zakresy_config[model]
        else:
            zakresy = zakresy_config['default']
        
        return {
            'Kp': tuple(zakresy['Kp']),
            'Ti': tuple(zakresy['Ti']),
            'Td': tuple(zakresy['Td'])
        }
    
    def pobierz_gestosc_siatki(self, regulator: str) -> Dict[str, int]:
        """
        Pobiera gęstość siatki dla danego regulatora.
        
        Args:
            regulator: Nazwa regulatora (np. 'regulator_pid')
        
        Returns:
            Słownik z liczbą punktów: {'Kp': n, 'Ti': m, 'Td': k}
        """
        return self.config['gestosc_siatki'].get(regulator, {'Kp': 20})
    
    def pobierz_wagi_kary(self) -> Dict[str, float]:
        """Pobiera wagi funkcji kary."""
        return self.config['wagi_kary']
    
    def czy_adaptacyjne_przeszukiwanie(self) -> bool:
        """Sprawdza czy włączone jest adaptacyjne przeszukiwanie."""
        return self.config['adaptacyjne_przeszukiwanie']['enabled']
    
    def pobierz_config_adaptacyjny(self) -> Dict[str, Any]:
        """Pobiera konfigurację adaptacyjnego przeszukiwania."""
        return self.config['adaptacyjne_przeszukiwanie']
    
    def pobierz_config_optymalizacji(self) -> Dict[str, Any]:
        """Pobiera konfigurację optymalizacji numerycznej."""
        return self.config['optymalizacja']
    
    def czy_rownolegle(self) -> bool:
        """Sprawdza czy włączone jest równoległe wykonywanie."""
        return self.config['rownolegle']['enabled']
    
    def pobierz_n_jobs(self) -> int:
        """Pobiera liczbę procesów dla równoległego wykonywania."""
        return self.config['rownolegle']['n_jobs']
    
    def pobierz_config_logowania(self) -> Dict[str, Any]:
        """Pobiera konfigurację logowania."""
        return self.config['logowanie']
    
    def pobierz_scenariusze_walidacji(self) -> List[Dict[str, Any]]:
        """Pobiera listę scenariuszy walidacji."""
        return self.config['walidacja']['scenariusze']
    
    def pobierz_progi_walidacji(self) -> Dict[str, float]:
        """Pobiera progi akceptacji dla walidacji."""
        return self.config['walidacja']['progi_akceptacji']
    
    def pobierz_config_raportowania(self) -> Dict[str, Any]:
        """Pobiera konfigurację raportowania."""
        return self.config['raportowanie']

# Globalna instancja konfiguracji (singleton)
_instancja_konfiguracji = None

def pobierz_konfiguracje() -> Konfiguracja:
    """
    Pobiera globalną instancję konfiguracji (singleton).
    
    Returns:
        Instancja klasy Konfiguracja
    """
    global _instancja_konfiguracji
    if _instancja_konfiguracji is None:
        _instancja_konfiguracji = Konfiguracja()
    return _instancja_konfiguracji

def zaladuj_konfiguracje_na_nowo(sciezka_config: str = None):
    """
    Przeładowuje konfigurację z pliku.
    
    Args:
        sciezka_config: Ścieżka do pliku config.yaml
    """
    global _instancja_konfiguracji
    _instancja_konfiguracji = Konfiguracja(sciezka_config)
    return _instancja_konfiguracji
