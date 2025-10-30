# -*- coding: utf-8 -*-
"""
Uruchomienie symulacji – wersja z:
- mapowaniem kluczy parametrów (case-insensitive) do sygnatury konstruktora regulatora,
- opcjonalnym DT z ENV (jeśli model przyjmuje `dt`/`DT`).
Reszta logiki pozostaje bez zmian merytorycznych.
"""

from __future__ import annotations
import importlib
import inspect
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict

# ---------------------------------------
# Pomocnicze: bezpieczny dynamiczny import
# ---------------------------------------

def dynamiczny_import(modul: str, nazwa: str | None = None) -> Any:
    """
    Załaduj moduł/klasę: jeśli `nazwa` jest None, zwraca moduł,
    w przeciwnym wypadku atrybut z modułu (np. klasę).
    """
    try:
        m = importlib.import_module(modul)
    except Exception as e:
        raise ImportError(f"Nie udało się zaimportować modułu '{modul}': {e}") from e

    if nazwa is None:
        return m

    try:
        return getattr(m, nazwa)
    except AttributeError as e:
        raise ImportError(f"Moduł '{modul}' nie ma atrybutu '{nazwa}'.") from e

# ---------------------------------------------------
# Mapowanie kluczy (case-insensitive) do sygnatury __init__
# ---------------------------------------------------

_SYNONIMY = {
    "kp": "Kp",
    "ti": "Ti",
    "td": "Td",
    "kr": "Kr",
    "umin": "umin",
    "umax": "umax",
    "dt": "dt",
}

def _dopasuj_kwargs_do_sygnatury(cls: type, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Dopasuj słownik `params` do sygnatury konstruktora `cls`:
    - case-insensitive,
    - mapowanie aliasów (kp→Kp itp.),
    - odrzucenie kluczy nieobecnych w __init__.

    Dzięki temu unikamy sytuacji, gdy regulator oczekuje `kp`, a mamy `Kp` (lub odwrotnie).
    """
    sig = inspect.signature(cls.__init__)
    akceptowane = {p.name for p in sig.parameters.values() if p.kind in (p.KEYWORD_ONLY, p.POSITIONAL_OR_KEYWORD)}
    # Zbierz mapę “obniżonych” nazw akceptowanych parametrów (dla case-insensitive)
    akceptowane_low = {name.lower(): name for name in akceptowane}

    wynik: Dict[str, Any] = {}
    for k, v in (params or {}).items():
        low = str(k).lower()
        # Najpierw znane synonimy (kp->Kp)
        if low in _SYNONIMY:
            cel = _SYNONIMY[low]
            if cel in akceptowane:
                wynik[cel] = v
                continue
        # Potem bezpośrednie (case-insensitive) dopasowanie do parametrów __init__
        if low in akceptowane_low:
            wynik[akceptowane_low[low]] = v
            continue
        # Jeśli nie ma dopasowania – pomijamy (bez wyjątku), by nie wywalać całej symulacji
    return wynik

# ---------------------------
# Główny punkt wejścia skryptu
# ---------------------------

def main() -> None:
    # Konfiguracja z ENV (zachowuję istniejące nazwy zmiennych)
    regulator_modul = os.getenv("REGULATOR", "regulator_pid")  # np. 'regulator_pid'
    model_modul     = os.getenv("MODEL",     "model_wahadlo")  # przykład
    sciezka_cfg     = os.getenv("KONFIG",    "src/konfiguracja.json")
    wyjscie_dir     = os.getenv("WYNIKI",    "wyniki")

    # Wczytaj konfigurację (jeśli masz inne źródło u siebie – zostaw)
    cfg_path = Path(sciezka_cfg)
    if not cfg_path.exists():
        print(f"[WARN] Brak pliku konfiguracji: {cfg_path} – użyję pustej.", file=sys.stderr)
        konfiguracja = {}
    else:
        with cfg_path.open("r", encoding="utf-8") as f:
            konfiguracja = json.load(f)

    # --- Dynamiczne klasy regulatora i modelu ---
    # Zakładam Twoją dotychczasową konwencję katalogów:
    #   src/regulatory/<regulator_modul>.py  -> klasa exportowana jako CamelCase na końcu (np. Regulator_PID)
    #   src/modele/<model_modul>.py          -> klasa modelu exportowana jako CamelCase
    # Jeżeli masz inną – dopasuj tylko te dwie linie nazw modułów/klas:
    klasa_regulatora = dynamiczny_import(f"src.regulatory.{regulator_modul}", nazwa=None)
    # heurystyka: bierz pierwszą klasę z modułu, której nazwa zaczyna się od "Regulator"
    RegClass = None
    for nazwa, ob in vars(klasa_regulatora).items():
        if inspect.isclass(ob) and nazwa.lower().startswith("regulator"):
            RegClass = ob
            break
    if RegClass is None:
        raise ImportError(f"Nie znaleziono klasy regulatora w module 'src.regulatory.{regulator_modul}'.")

    klasa_modelu_mod = dynamiczny_import(f"src.modele.{model_modul}", nazwa=None)
    ModelClass = None
    for nazwa, ob in vars(klasa_modelu_mod).items():
        if inspect.isclass(ob):
            ModelClass = ob
            break
    if ModelClass is None:
        raise ImportError(f"Nie znaleziono klasy modelu w module 'src.modele.{model_modul}'.")

    # --- Parametry z konfiguracji (jeśli masz w JSON, to się zmerguje) ---
    paramy_reg = konfiguracja.get("regulator", {})
    paramy_mod = konfiguracja.get("model", {})

    # Wstrzyknięcie DT z ENV (nienachalne): jeśli konstruktor modelu przyjmuje 'dt' lub 'DT'
    dt_env = os.getenv("DT")
    if dt_env is not None:
        try:
            dt_val = float(dt_env)
            # spróbuj podać jako 'dt' (albo 'DT') tylko jeśli są w sygnaturze
            sig_m = inspect.signature(ModelClass.__init__)
            names = {p.name.lower() for p in sig_m.parameters.values()}
            if "dt" in names or "DT".lower() in names:
                paramy_mod = dict(paramy_mod)  # kopia
                paramy_mod["dt"] = dt_val
        except ValueError:
            print(f"[WARN] DT='{dt_env}' nie jest liczbą – ignoruję.", file=sys.stderr)

    # --- Utworzenie instancji modelu i regulatora z mapowaniem kluczy ---
    paramy_mod_mapped = _dopasuj_kwargs_do_sygnatury(ModelClass, paramy_mod)
    model = ModelClass(**paramy_mod_mapped)

    paramy_reg_mapped = _dopasuj_kwargs_do_sygnatury(RegClass, paramy_reg)
    regulator = RegClass(**paramy_reg_mapped)

    # --- Tutaj pozostawiam Twoją istniejącą logikę symulacji/raportowania ---
    # Pseudokod – ZASTĄP go swoim dotychczasowym przebiegiem (jeśli poniżej już coś masz, użyj tego fragmentu tylko jako referencji):
    #   - zadaj wejście (skok itp.)
    #   - pętla po czasie: regulator(e(t)) -> u(t) -> model -> y(t)
    #   - zebrane dane -> metryki -> raporty/wykresy do `wyjscie_dir`
    #
    # Przykładowy print, żeby było widać że działa:
    print(f"[INFO] Uruchomiono: regulator={RegClass.__name__}, model={ModelClass.__name__}")
    print(f"[INFO] Parametry regulatora (po mapowaniu): {paramy_reg_mapped}")
    print(f"[INFO] Parametry modelu (po mapowaniu):     {paramy_mod_mapped}")
    print(f"[INFO] WYNIKI -> {wyjscie_dir}")

if __name__ == "__main__":
    main()
