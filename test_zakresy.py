"""
Test wczytywania nowych zakresów parametrów.
"""
import sys
sys.path.insert(0, 'C:\\Users\\Laptop\\Desktop\\Git\\PID-CD')

from src.konfig import pobierz_konfiguracje

config = pobierz_konfiguracje()

print("=== TEST ZAKRESÓW PARAMETRÓW ===\n")

modele = ["zbiornik_1rz", "dwa_zbiorniki", "wahadlo_odwrocone"]

for model in modele:
    print(f"Model: {model}")
    zakresy = config.pobierz_zakresy("regulator_pid", model)
    print(f"  Kp: {zakresy['Kp']}")
    print(f"  Ti: {zakresy['Ti']}")
    print(f"  Td: {zakresy['Td']}")
    print()

print("=== TEST WAG KARY ===\n")
wagi = config.pobierz_wagi_kary()
print(f"Przeregulowanie: {wagi.get('przeregulowanie')}")
print(f"Czas ustalania: {wagi.get('czas_ustalania')}")
print(f"Parametry ekstremalne: {wagi.get('parametry_ekstremalne')}")

print("\n=== TEST PROGÓW WALIDACJI ===\n")
progi = config.pobierz_progi_walidacji()
print(f"IAE_max: {progi.get('IAE_max')}")
print(f"Mp_max: {progi.get('przeregulowanie_max')}")
print(f"ts_max: {progi.get('czas_ustalania_max')}")
