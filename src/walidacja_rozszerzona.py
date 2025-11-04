"""
Moduł rozszerzonej walidacji regulatorów.
Testuje regulatory w różnych scenariuszach:
- Różne wielkości skoków wartości zadanej
- Zakłócenia na wyjściu
- Szum pomiarowy
"""

import os
import json
import numpy as np
import matplotlib.pyplot as plt
from typing import Dict, List, Any
import sys

# Dodaj katalog src do PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from metryki import oblicz_metryki
from konfig import pobierz_konfiguracje


def dynamiczny_import(typ: str, nazwa: str):
    """Dynamicznie importuje klasę modelu lub regulatora po nazwie."""
    import importlib
    modul = importlib.import_module(f"src.{typ}.{nazwa}")
    for attr in dir(modul):
        if attr.lower() == nazwa.lower():
            return getattr(modul, attr)
    return getattr(modul, [a for a in dir(modul) if not a.startswith("_")][0])


def symuluj_scenariusz(
    ModelClass, 
    RegulatorClass, 
    parametry: Dict, 
    scenariusz: Dict,
    czas_sym: float = 120.0
) -> Dict[str, Any]:
    """
    Wykonuje symulację w danym scenariuszu.
    
    Args:
        ModelClass: Klasa modelu
        RegulatorClass: Klasa regulatora
        parametry: Parametry regulatora
        scenariusz: Słownik opisujący scenariusz testowy
        czas_sym: Czas symulacji w sekundach
    
    Returns:
        Dict z wynikami: t, r, y, u, metryki
    """
    model = ModelClass()
    dt = model.dt
    
    # Filtruj parametry do sygnatury konstruktora
    import inspect
    sig = inspect.signature(RegulatorClass.__init__)
    parametry_filtr = {k: v for k, v in parametry.items() if k in sig.parameters and v is not None}
    regulator = RegulatorClass(**parametry_filtr, dt=dt, umin=None, umax=None)
    
    kroki = int(czas_sym / dt)
    t, r, y, u = [], [], [], []
    
    typ_scenariusza = scenariusz['typ']
    
    # Określ wartość zadaną bazową
    model_nazwa = ModelClass.__name__.lower()
    r_bazowe = 0.0 if 'wahadlo' in model_nazwa else 1.0
    
    for k in range(kroki):
        czas_k = k * dt
        t.append(czas_k)
        
        # === Wartość zadana ===
        if typ_scenariusza == 'setpoint_step':
            # Skok wartości zadanej
            czas_skoku = scenariusz.get('czas_skoku', 10.0)
            wielkosc = scenariusz.get('wielkosc', 10.0)
            
            if czas_k < czas_skoku:
                r_k = r_bazowe
            else:
                r_k = r_bazowe + wielkosc
        else:
            # Domyślna wartość zadana
            r_k = r_bazowe
        
        r.append(r_k)
        
        # === Pomiar (z możliwym szumem) ===
        y_k = model.y
        
        if typ_scenariusza == 'measurement_noise':
            # Dodaj szum gaussowski do pomiaru
            szum_std = scenariusz.get('odchylenie_std', 0.1)
            y_k_zaszumiony = y_k + np.random.normal(0, szum_std)
        else:
            y_k_zaszumiony = y_k
        
        # === Sterowanie ===
        u_k = regulator.update(r_k, y_k_zaszumiony)
        
        # === Zakłócenie na wyjściu ===
        if typ_scenariusza == 'output_disturbance':
            czas_zaklocenia = scenariusz.get('czas_zaklócenia', 60.0)
            wielkosc_zaklocenia = scenariusz.get('wielkosc', -3.0)
            
            if czas_k >= czas_zaklocenia:
                # Zakłócenie jako dodatkowa składowa sterowania
                u_k_z_zaklóceniem = u_k + wielkosc_zaklocenia
            else:
                u_k_z_zaklóceniem = u_k
            
            y_nowe = model.step(u_k_z_zaklóceniem)
        else:
            y_nowe = model.step(u_k)
        
        y.append(y_nowe)
        u.append(u_k)
    
    # Oblicz metryki
    metryki = oblicz_metryki(t, r, y, u)
    
    return {
        't': t,
        'r': r,
        'y': y,
        'u': u,
        'metryki': metryki.__dict__
    }


def walidacja_rozszerzona(
    regulator_nazwa: str,
    metoda: str,
    model_nazwa: str,
    parametry: Dict,
    katalog_wyniki: str = "wyniki"
) -> Dict[str, Any]:
    """
    Przeprowadza rozszerzoną walidację regulatora w wielu scenariuszach.
    
    Returns:
        Dict z wynikami dla wszystkich scenariuszy
    """
    print(f"\n🧪 Rozszerzona walidacja: {regulator_nazwa} / {metoda} na modelu {model_nazwa}")
    
    # Wczytaj konfigurację
    config = pobierz_konfiguracje()
    scenariusze = config.pobierz_scenariusze_walidacji()
    progi = config.pobierz_progi_walidacji()
    
    # Import klas
    ModelClass = dynamiczny_import("modele", model_nazwa)
    RegulatorClass = dynamiczny_import("regulatory", regulator_nazwa)
    
    wyniki_wszystkie_scenariusze = []
    pass_count = 0
    
    for idx, scenariusz in enumerate(scenariusze):
        nazwa_scenariusza = scenariusz['nazwa']
        print(f"\n  📋 Scenariusz {idx+1}/{len(scenariusze)}: {nazwa_scenariusza}")
        
        # Wykonaj symulację
        try:
            wynik = symuluj_scenariusz(ModelClass, RegulatorClass, parametry, scenariusz)
            
            # Sprawdź progi
            metryki = wynik['metryki']
            pass_gates = True
            powod = []
            
            # Sprawdź reakcję regulatora
            if np.std(wynik['u']) < 1e-4:
                pass_gates = False
                powod.append("brak reakcji (u ~ const)")
            
            # Sprawdź metryki
            if metryki['IAE'] > progi['IAE_max']:
                pass_gates = False
                powod.append(f"IAE={metryki['IAE']:.2f} > {progi['IAE_max']}")
            
            if metryki['przeregulowanie'] > progi['przeregulowanie_max']:
                pass_gates = False
                powod.append(f"Mp={metryki['przeregulowanie']:.1f}% > {progi['przeregulowanie_max']}%")
            
            if metryki['czas_ustalania'] > progi['czas_ustalania_max']:
                pass_gates = False
                powod.append(f"ts={metryki['czas_ustalania']:.1f}s > {progi['czas_ustalania_max']}s")
            
            if pass_gates:
                pass_count += 1
                print(f"    ✅ PASS - IAE={metryki['IAE']:.2f}, Mp={metryki['przeregulowanie']:.1f}%, ts={metryki['czas_ustalania']:.1f}s")
            else:
                print(f"    ❌ FAIL - {', '.join(powod)}")
            
            wynik_scenariusza = {
                'scenariusz': nazwa_scenariusza,
                'typ': scenariusz['typ'],
                'pass': pass_gates,
                'powod': powod,
                'metryki': metryki,
                't': wynik['t'],
                'r': wynik['r'],
                'y': wynik['y'],
                'u': wynik['u']
            }
            
            wyniki_wszystkie_scenariusze.append(wynik_scenariusza)
            
        except Exception as e:
            print(f"    ⚠️ Błąd podczas symulacji: {e}")
            wyniki_wszystkie_scenariusze.append({
                'scenariusz': nazwa_scenariusza,
                'typ': scenariusz['typ'],
                'pass': False,
                'powod': [f"Błąd symulacji: {e}"],
                'metryki': None
            })
    
    # Podsumowanie
    procent_pass = (pass_count / len(scenariusze)) * 100
    print(f"\n  📊 Wynik końcowy: {pass_count}/{len(scenariusze)} scenariuszy zaliczonych ({procent_pass:.1f}%)")
    
    # Generuj wykres porównawczy
    _generuj_wykres_scenariusze(wyniki_wszystkie_scenariusze, regulator_nazwa, metoda, model_nazwa, katalog_wyniki)
    
    # Zapisz raport JSON
    raport = {
        'regulator': regulator_nazwa,
        'metoda': metoda,
        'model': model_nazwa,
        'parametry': parametry,
        'scenariusze': wyniki_wszystkie_scenariusze,
        'podsumowanie': {
            'zaliczonych': pass_count,
            'wszystkich': len(scenariusze),
            'procent': procent_pass
        }
    }
    
    raport_path = os.path.join(katalog_wyniki, f"raport_rozszerzony_{regulator_nazwa}_{metoda}_{model_nazwa}.json")
    
    # Konwertuj numpy arrays na listy dla JSON
    for scen in raport['scenariusze']:
        if scen.get('t'):
            scen['t'] = [float(x) for x in scen['t'][:100]]  # Ogranicz do 100 punktów
            scen['r'] = [float(x) for x in scen['r'][:100]]
            scen['y'] = [float(x) for x in scen['y'][:100]]
            scen['u'] = [float(x) for x in scen['u'][:100]]
    
    with open(raport_path, 'w', encoding='utf-8') as f:
        json.dump(raport, f, indent=2)
    
    print(f"  💾 Zapisano raport: {raport_path}")
    
    return raport


def _generuj_wykres_scenariusze(
    wyniki: List[Dict],
    regulator_nazwa: str,
    metoda: str,
    model_nazwa: str,
    katalog_wyniki: str
):
    """Generuje wykres porównawczy dla wszystkich scenariuszy."""
    
    # Filtruj tylko scenariusze z danymi
    wyniki_z_danymi = [w for w in wyniki if w.get('t') is not None]
    
    if not wyniki_z_danymi:
        print("  ⚠️ Brak danych do wygenerowania wykresu")
        return
    
    n_scenariuszy = len(wyniki_z_danymi)
    fig, axes = plt.subplots(n_scenariuszy, 2, figsize=(14, 4*n_scenariuszy))
    
    if n_scenariuszy == 1:
        axes = axes.reshape(1, -1)
    
    fig.suptitle(f'Rozszerzona walidacja: {regulator_nazwa} / {metoda} na {model_nazwa}', 
                 fontsize=14, fontweight='bold')
    
    for idx, wynik in enumerate(wyniki_z_danymi):
        ax_y = axes[idx, 0]
        ax_u = axes[idx, 1]
        
        # Wykres odpowiedzi
        ax_y.plot(wynik['t'], wynik['r'], 'k--', label='Wartość zadana', alpha=0.7)
        ax_y.plot(wynik['t'], wynik['y'], 'b-', label='Odpowiedź', linewidth=2)
        ax_y.set_ylabel('Wartość')
        ax_y.grid(True, alpha=0.3)
        ax_y.legend(loc='best')
        
        status = "✅ PASS" if wynik['pass'] else "❌ FAIL"
        ax_y.set_title(f"{wynik['scenariusz']} - {status}", fontweight='bold')
        
        # Wykres sterowania
        ax_u.plot(wynik['t'], wynik['u'], 'r-', label='Sterowanie', linewidth=1.5)
        ax_u.set_ylabel('Sterowanie')
        ax_u.set_xlabel('Czas [s]')
        ax_u.grid(True, alpha=0.3)
        ax_u.legend(loc='best')
        
        # Dodaj metryki
        if wynik['metryki']:
            m = wynik['metryki']
            info = f"IAE={m['IAE']:.2f}, Mp={m['przeregulowanie']:.1f}%, ts={m['czas_ustalania']:.1f}s"
            ax_y.text(0.02, 0.98, info, transform=ax_y.transAxes, 
                     verticalalignment='top', fontsize=8,
                     bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    plt.tight_layout()
    wykres_path = os.path.join(katalog_wyniki, 
                               f"walidacja_rozszerzona_{regulator_nazwa}_{metoda}_{model_nazwa}.png")
    plt.savefig(wykres_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"  📊 Zapisano wykres: {wykres_path}")


if __name__ == "__main__":
    # Test
    parametry_test = {"Kp": 15.0, "Ti": 50.0, "Td": 0.1}
    walidacja_rozszerzona("regulator_pid", "optymalizacja", "zbiornik_1rz", parametry_test)
