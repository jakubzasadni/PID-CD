"""Szybka walidacja nowych parametrów PD i PID dla dwa_zbiorniki"""
import sys
sys.path.insert(0, r'c:\Users\Laptop\Desktop\Git\PID-CD')

import numpy as np
from src.modele.dwa_zbiorniki import Dwa_zbiorniki
from src.regulatory.regulator_pd import regulator_pd
from src.regulatory.regulator_pid import Regulator_PID
from src.metryki import oblicz_metryki

def waliduj_regulator(Regulator, params, nazwa):
    """Walidacja pojedynczego regulatora"""
    model = Dwa_zbiorniki()
    reg = Regulator(**params, dt=0.05)
    
    T = np.arange(0, 120, 0.05)
    y = []
    u_sig = []
    setpoint = 1.0
    
    for t in T:
        e = setpoint - model.y
        # PD i PID wymagają wartości y jako drugi argument, P nie
        if 'Td' in params:  # PD lub PID
            u = reg.update(e, model.y)
        else:  # P lub PI
            u = reg.update(e)
        y.append(model.y)
        u_sig.append(u)
        model.step(u)
    
    metryki = oblicz_metryki(T, np.array(y), np.array(u_sig), setpoint)
    
    # Progi dla dwa_zbiorniki
    PASS = (metryki.przeregulowanie <= 20.0 and 
            metryki.czas_ustalania <= 120.0 and 
            metryki.IAE <= 80.0)
    
    print(f"\n{nazwa}:")
    print(f"  Parametry: {params}")
    print(f"  IAE={metryki.IAE:.2f}, Mp={metryki.przeregulowanie:.1f}%, ts={metryki.czas_ustalania:.1f}s")
    print(f"  Status: {'[OK] PASS' if PASS else '[X] FAIL'}")
    if not PASS:
        problemy = []
        if metryki.przeregulowanie > 20.0:
            problemy.append(f"Mp={metryki.przeregulowanie:.1f}% > 20%")
        if metryki.czas_ustalania > 120.0:
            problemy.append(f"ts={metryki.czas_ustalania:.1f}s > 120s")
        if metryki.IAE > 80.0:
            problemy.append(f"IAE={metryki.IAE:.2f} > 80")
        print(f"  Problemy: {', '.join(problemy)}")
    
    return PASS, metryki

print("="*70)
print("WALIDACJA NOWYCH PARAMETRÓW DLA MODELU: dwa_zbiorniki")
print("="*70)

# Stare parametry (do porównania)
print("\n🔴 STARE PARAMETRY (przed poprawką):")
waliduj_regulator(regulator_pd, {'Kp': 8.41, 'Td': 0.11}, "PD optymalizacja (stare)")
waliduj_regulator(Regulator_PID, {'Kp': 24.94, 'Ti': 30.0, 'Td': 0.06}, "PID optymalizacja (stare)")

# Nowe parametry
print("\n\n🟢 NOWE PARAMETRY (po poprawce zakresów):")
waliduj_regulator(regulator_pd, {'Kp': 10.0, 'Td': 1.97}, "PD siatka (nowe)")
waliduj_regulator(regulator_pd, {'Kp': 10.0, 'Td': 1.95}, "PD optymalizacja (nowe)")
waliduj_regulator(Regulator_PID, {'Kp': 10.0, 'Ti': 100.0, 'Td': 1.92}, "PID siatka (nowe)")

print("\n" + "="*70)
print("PODSUMOWANIE")
print("="*70)
print("Nowe zakresy w config.yaml:")
print("  Kp: [0.1, 10.0]  (było: [0.1, 25.0])")
print("  Ti: [10.0, 100.0] (było: [2.0, 60.0])")
print("  Td: [0.1, 5.0]   (było: [0.1, 15.0])")
