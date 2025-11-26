"""
Debug wczytywania konfiguracji.
"""
import sys
import os
sys.path.insert(0, 'C:\\Users\\Laptop\\Desktop\\Git\\PID-CD')

from pathlib import Path

print("=== DEBUG WCZYTYWANIA CONFIG ===\n")

# Sprawdź gdzie jest config.yaml
config_path = Path('C:\\Users\\Laptop\\Desktop\\Git\\PID-CD\\src\\config.yaml')
print(f"Ścieżka do config.yaml: {config_path}")
print(f"Plik istnieje: {config_path.exists()}")

if config_path.exists():
    import yaml
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    print("\n=== Zakresy z pliku ===")
    print(f"default Kp: {config['zakresy_parametrow']['default']['Kp']}")
    print(f"default Ti: {config['zakresy_parametrow']['default']['Ti']}")
    print(f"default Td: {config['zakresy_parametrow']['default']['Td']}")
    
    print("\n=== zbiornik_1rz ===")
    if 'zbiornik_1rz' in config['zakresy_parametrow']:
        print(f"Kp: {config['zakresy_parametrow']['zbiornik_1rz']['Kp']}")
        print(f"Ti: {config['zakresy_parametrow']['zbiornik_1rz']['Ti']}")
        print(f"Td: {config['zakresy_parametrow']['zbiornik_1rz']['Td']}")

print("\n=== Testowanie konfig.py ===")
from src.konfig import pobierz_konfiguracje

cfg = pobierz_konfiguracje()
zakresy = cfg.pobierz_zakresy("regulator_pid", "zbiornik_1rz")
print(f"Przez konfig.py - Kp: {zakresy['Kp']}")
print(f"Przez konfig.py - Ti: {zakresy['Ti']}")
print(f"Przez konfig.py - Td: {zakresy['Td']}")
