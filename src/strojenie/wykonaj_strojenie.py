"""
Moduł wywołujący różne metody strojenia regulatorów.
Zwraca zestaw parametrów do testów walidacyjnych i generuje raport HTML.
Obsługiwane regulatory: regulator_p, regulator_pi, regulator_pd, regulator_pid.
"""

import os
import json
import importlib
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime

from src.metryki import oblicz_metryki


# ------------------------------------------------------------
# Funkcja pomocnicza - dynamiczny import
# ------------------------------------------------------------
def _dynamiczny_import(typ: str, nazwa: str):
    """Dynamicznie importuje klasę modelu lub regulatora."""
    modul = importlib.import_module(f"src.{typ}.{nazwa}")
    for attr in dir(modul):
        if attr.lower() == nazwa.lower():
            return getattr(modul, attr)
    return getattr(modul, [a for a in dir(modul) if not a.startswith("_")][0])


# ------------------------------------------------------------
# Funkcja pomocnicza - symulacja testowa dla tuningu
# ------------------------------------------------------------
def _uruchom_symulacje_testowa(RegulatorClass, parametry: dict, model_nazwa: str, czas_sym=120.0):
    """
    Uruchamia symulację z podanymi parametrami regulatora i modelu.
    Zwraca wyniki metryk (IAE, Mp, ts, tr) oraz funkcję kary.
    
    Args:
        RegulatorClass: Klasa regulatora (regulator_p, regulator_pi, etc.)
        parametry: dict z parametrami {"Kp": 1.0, "Ti": 10.0, "Td": 3.0, ...}
        model_nazwa: nazwa modelu ("zbiornik_1rz", "dwa_zbiorniki", "wahadlo_odwrocone")
        czas_sym: czas symulacji w sekundach
        
    Returns:
        tuple: (wyniki_metryki, funkcja_kary)
    """
    try:
        # Import modelu
        ModelClass = _dynamiczny_import("modele", model_nazwa)
        model = ModelClass()
        dt = model.dt
        
        # Filtruj parametry do sygnatury konstruktora
        import inspect
        sig = inspect.signature(RegulatorClass.__init__)
        parametry_filtr = {k: v for k, v in parametry.items() if k in sig.parameters and v is not None}
        
        # Dla strojenia: usuń limity saturacji (umin, umax) żeby regulator mógł swobodnie działać
        # Model sam zadba o fizyczne ograniczenia
        # Stwórz regulator z parametrami - UWAGA: Dla przemysłu dodaj realistyczne limity
        regulator = RegulatorClass(**parametry_filtr, dt=dt, umin=-15.0, umax=15.0)
        
        # Symulacja
        kroki = int(czas_sym / dt)
        t, r, y, u = [], [], [], []
        
        # Wartość zadana zależna od modelu
        r_zad = 0.0 if model_nazwa == "wahadlo_odwrocone" else 1.0
        
        for k in range(kroki):
            t.append(k * dt)
            y_k = model.y
            u_k = regulator.update(r_zad, y_k)
            y_nowe = model.step(u_k)
            r.append(r_zad)
            y.append(y_nowe)
            u.append(u_k)
        
        # Oblicz metryki
        wyniki = oblicz_metryki(t, r, y, u)

        # Wczytaj wagi funkcji kary z konfiguracji
        try:
            import sys
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            from konfig import pobierz_konfiguracje
            cfg = pobierz_konfiguracje()
            wagi = cfg.pobierz_wagi_kary()
            zakresy = cfg.pobierz_zakresy_parametrow(model_nazwa)
            w_mp = float(wagi.get('przeregulowanie', 0.5))
            w_ts = float(wagi.get('czas_ustalania', 1.0))
            w_const = float(wagi.get('sterowanie_stale', 1000))
            w_extreme = float(wagi.get('parametry_ekstremalne', 50))
        except Exception:
            w_mp, w_ts, w_const, w_extreme = 0.5, 1.0, 1000.0, 50.0
            zakresy = {}

        # Funkcja kary (niższa = lepsza)
        # Priorytet: IAE + kara za przeregulowanie + kara za wolne ustalanie
        kara = wyniki.IAE + w_mp * wyniki.przeregulowanie + w_ts * wyniki.czas_ustalania

        # Dodatkowa kara za niestabilność (jeśli regulator nie reaguje)
        if np.std(u) < 1e-4:
            kara += w_const
        
        # Kara za parametry zbliżone do granic zakresu (preferuj wartości środkowe)
        if zakresy:
            kp = parametry.get('Kp', 0)
            ti = parametry.get('Ti', None)
            td = parametry.get('Td', None)
            
            # Penalizuj Kp bliskie GÓRNEJ granicy (>70% zakresu)
            if 'Kp' in zakresy:
                kp_min, kp_max = zakresy['Kp']
                if kp > kp_min + 0.7 * (kp_max - kp_min):
                    przekroczenie = (kp - (kp_min + 0.7*(kp_max - kp_min))) / (0.3*(kp_max - kp_min))
                    kara += w_extreme * przekroczenie * przekroczenie  # Kara kwadratowa
            
            # Penalizuj Ti bliskie GÓRNEJ granicy (>70% zakresu) 
            if ti and 'Ti' in zakresy:
                ti_min, ti_max = zakresy['Ti']
                if ti > ti_min + 0.7 * (ti_max - ti_min):
                    przekroczenie = (ti - (ti_min + 0.7*(ti_max - ti_min))) / (0.3*(ti_max - ti_min))
                    kara += w_extreme * przekroczenie * przekroczenie  # Kara kwadratowa
            
            # Penalizuj Td bliskie DOLNEJ granicy (<20% zakresu) - chcemy WYŻSZYCH wartości Td
            if td and 'Td' in zakresy:
                td_min, td_max = zakresy['Td']
                if td < td_min + 0.2 * (td_max - td_min):
                    przekroczenie = ((td_min + 0.2*(td_max - td_min)) - td) / (0.2*(td_max - td_min))
                    kara += 2.0 * w_extreme * przekroczenie * przekroczenie  # Podwójna kara za NISKIE Td
        
        return wyniki, kara
        
    except Exception as e:
        # W przypadku błędu (np. niestabilność) zwróć wysoką karę
        try:
            import logging
            logging.exception(f"Błąd symulacji podczas strojenia: {e}")
        except Exception:
            print(f"[UWAGA] Błąd symulacji: {e}")
        class DummyMetryki:
            IAE = 999999
            przeregulowanie = 999
            czas_ustalania = 999
            czas_narastania = 999
        return DummyMetryki(), 999999.0


# ------------------------------------------------------------
# Pomocnicze funkcje formatowania i filtrowania
# ------------------------------------------------------------
def _get(params: dict, keys, default=None):
    for k in keys:
        if k in params:
            return params[k]
    return default


def _round_or_none(x, ndigits=2):
    if x is None:
        return None
    try:
        return round(float(x), ndigits)
    except Exception:
        return None


def _filter_for_regulator(reg_name: str, params: dict) -> dict:
    """Zwraca tylko te parametry, które mają sens dla danego typu regulatora."""
    reg = reg_name.lower()
    kp = _get(params, ["Kp", "kp"], 1.0)
    ti = _get(params, ["Ti", "ti"], None)
    td = _get(params, ["Td", "td"], None)

    if reg == "regulator_p":
        return {"Kp": _round_or_none(kp), "Ti": None, "Td": None}
    if reg == "regulator_pi":
        return {"Kp": _round_or_none(kp), "Ti": _round_or_none(ti), "Td": None}
    if reg == "regulator_pd":
        return {"Kp": _round_or_none(kp), "Ti": None, "Td": _round_or_none(td)}
    return {"Kp": _round_or_none(kp), "Ti": _round_or_none(ti), "Td": _round_or_none(td)}


# ------------------------------------------------------------
# Generacja raportu HTML
# ------------------------------------------------------------
def _zapisz_raport_html(meta, parametry, historia=None, out_dir="wyniki"):
    os.makedirs(out_dir, exist_ok=True)
    html_path = os.path.join(out_dir, f"raport_strojenie_{meta['regulator']}_{meta['metoda']}.html")

    with open(html_path, "w", encoding="utf-8") as f:
        f.write("<html><head><meta charset='utf-8'>")
        f.write(f"<title>Raport strojenia – {meta['regulator']} / {meta['metoda']}</title>")
        f.write("<style>body{font-family:Arial,sans-serif;margin:20px;} "
                "table{border-collapse:collapse;} td,th{border:1px solid #aaa;padding:6px;} "
                "th{background:#ddd;} h2{color:#333;}</style></head><body>")
        f.write(f"<h2>📘 Raport strojenia – {meta['regulator']} / {meta['metoda']}</h2>")
        f.write(f"<p>Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>")

        # Tabela parametrów
        f.write("<table><tr><th>Parametr</th><th>Wartość</th></tr>")
        for k in ["Kp", "Ti", "Td"]:
            val = parametry.get(k)
            f.write(f"<tr><td>{k}</td><td>{'-' if val is None else val}</td></tr>")
        f.write("</table>")

        # Czas obliczeń (opcjonalnie)
        try:
            import sys
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            from konfig import pobierz_konfiguracje
            cfg = pobierz_konfiguracje().pobierz_config_raportowania()
            if cfg.get('pokaz_czas_obliczen') and meta.get('czas_obliczen_s') is not None:
                f.write(f"<p><strong>Czas obliczeń:</strong> {meta['czas_obliczen_s']:.2f} s</p>")
        except Exception:
            pass

        # wykres postępu optymalizacji
        if historia and len(historia) > 1:
            plt.figure()
            plt.plot(historia)
            plt.xlabel("Iteracja")
            plt.ylabel("Funkcja celu")
            plt.title(f"Postęp optymalizacji – {meta['metoda']}")
            wykres_path = os.path.join(out_dir, f"strojenie_{meta['regulator']}_{meta['metoda']}.png")
            plt.savefig(wykres_path, dpi=120)
            plt.close()
            f.write(f"<p><img src='strojenie_{meta['regulator']}_{meta['metoda']}.png' width='600'></p>")

        f.write("</body></html>")

    print(f"[OK] Zapisano raport HTML: {html_path}")
    return html_path


# ------------------------------------------------------------
# Główna funkcja strojenia
# ------------------------------------------------------------
def wykonaj_strojenie(metoda="ziegler_nichols", model_nazwa="zbiornik_1rz"):
    """
    Główna funkcja strojenia regulatora z użyciem prawdziwych symulacji.
    
    Args:
        metoda: "ziegler_nichols", "siatka", "optymalizacja"
        model_nazwa: nazwa modelu do testowania (domyślnie "zbiornik_1rz")
        
    Returns:
        dict: parametry regulatora
    """
    # Katalog wyników: respektuj OUT_DIR z pipeline, fallback do 'wyniki'
    out_dir = os.getenv("OUT_DIR", "wyniki")
    os.makedirs(out_dir, exist_ok=True)

    regulator_nazwa = os.getenv("REGULATOR", "regulator_pid").lower()
    print(f"\n{'='*60}")
    print(f"[STROJENIE] Strojenie: {regulator_nazwa} | metoda: {metoda} | model: {model_nazwa}")
    print(f"{'='*60}")
    
    # Konfiguruj logowanie
    import logging
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from konfig import pobierz_konfiguracje
    
    config = pobierz_konfiguracje()
    config_log = config.pobierz_config_logowania()
    
    os.makedirs(os.path.dirname(config_log['plik_log']), exist_ok=True)
    logging.basicConfig(
        level=getattr(logging, config_log['poziom']),
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(config_log['plik_log'], encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    
    # Import klasy regulatora
    RegulatorClass = _dynamiczny_import("regulatory", regulator_nazwa)
    
    # --- 1) Wyznacz parametry używając prawdziwych symulacji ---
    historia = []
    params_zn = None  # Do przekazania jako punkt startowy dla optymalizacji
    
    import time
    start_time = time.time()

    if metoda == "ziegler_nichols":
        from src.strojenie.ziegler_nichols import strojenie_ZN
        pelne = strojenie_ZN(RegulatorClass, model_nazwa, regulator_nazwa)
        params_zn = pelne  # Zapisz dla ewentualnego użycia

    elif metoda == "siatka":
        from src.strojenie.przeszukiwanie_siatki import strojenie_siatka
        pelne = strojenie_siatka(RegulatorClass, model_nazwa, regulator_nazwa, 
                                _uruchom_symulacje_testowa)

    elif metoda == "optymalizacja":
        from src.strojenie.optymalizacja_numeryczna import strojenie_optymalizacja
        
        # Najpierw uruchom ZN aby uzyskać punkt startowy (jeśli skonfigurowane)
        if config.pobierz_config_optymalizacji()['punkty_startowe']['uzyj_ziegler_nichols']:
            try:
                from src.strojenie.ziegler_nichols import strojenie_ZN
                params_zn = strojenie_ZN(RegulatorClass, model_nazwa, regulator_nazwa)
                print(f"[INFO] Użyję parametrów ZN jako punktu startowego: {params_zn}")
            except Exception as e:
                logging.warning(f"Nie udało się uzyskać parametrów ZN: {e}")
                params_zn = None
        
        pelne, historia = strojenie_optymalizacja(RegulatorClass, model_nazwa, regulator_nazwa,
                                                  _uruchom_symulacje_testowa, params_zn)

    else:
        raise ValueError(f"[X] Nieznana metoda strojenia: {metoda}")

    czas_obliczen_s = time.time() - start_time

    # --- 2) Przytnij do typu regulatora i zaokrąglij ---
    params = _filter_for_regulator(regulator_nazwa, pelne)

    # --- 3) Zapisz JSON + raport HTML ---
    meta = {"regulator": regulator_nazwa, "metoda": metoda, "model": model_nazwa, "czas_obliczen_s": czas_obliczen_s}
    out = {"regulator": regulator_nazwa, "metoda": metoda, "model": model_nazwa, "parametry": params, "czas_obliczen_s": czas_obliczen_s}

    json_path = os.path.join(out_dir, f"parametry_{regulator_nazwa}_{metoda}_{model_nazwa}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(f" Zapisano parametry: {json_path}")

    _zapisz_raport_html(meta, params, historia, out_dir)
    return params


# ------------------------------------------------------------
# Test lokalny
# ------------------------------------------------------------
if __name__ == "__main__":
    for m in ["ziegler_nichols", "siatka", "optymalizacja"]:
        wykonaj_strojenie(m)
