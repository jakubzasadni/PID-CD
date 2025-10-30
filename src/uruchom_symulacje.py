# -*- coding: utf-8 -*-
"""
Uruchamianie symulacji – wersja utwardzona (bez zmian architektury):
- mapowanie nazw parametrów (case-insensitive) do __init__ regulatora/modelu,
- opcjonalny DT z ENV (jeśli model przyjmuje 'dt'),
- autodetekcja modułów modelu/regulatora z katalogów src/modele oraz src/regulatory,
  gdy domyślna nazwa nie istnieje (zapobiega ModuleNotFoundError).
"""

from __future__ import annotations
import importlib
import inspect
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple


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
    - mapowanie aliasów (kp->Kp itp.),
    - odrzucenie kluczy nieobecnych w __init__.
    """
    sig = inspect.signature(cls.__init__)
    akceptowane = {p.name for p in sig.parameters.values() if p.kind in (p.KEYWORD_ONLY, p.POSITIONAL_OR_KEYWORD)}
    akceptowane_low = {name.lower(): name for name in akceptowane}

    wynik: Dict[str, Any] = {}
    for k, v in (params or {}).items():
        low = str(k).lower()
        # Znane synonimy (kp->Kp)
        if low in _SYNONIMY:
            cel = _SYNONIMY[low]
            if cel in akceptowane:
                wynik[cel] = v
                continue
        # Bezpośrednie dopasowanie (case-insensitive)
        if low in akceptowane_low:
            wynik[akceptowane_low[low]] = v
            continue
        # brak dopasowania → ignorujemy ten klucz
    return wynik


# ---------------------------------------------------
# Autodetekcja nazw modułów w repo (nie zmienia struktury)
# ---------------------------------------------------

def _listuj_moduly_w_katalogu(katalog: Path) -> List[str]:
    """Zwróć listę nazw modułów (bez .py) w podanym katalogu."""
    if not katalog.exists():
        return []
    return sorted([p.stem for p in katalog.glob("*.py") if p.name != "__init__.py"])

def _znormalizuj(nazwa: str) -> str:
    return nazwa.lower().replace("_", "").replace("-", "")

def _wybierz_modul_z_fallbackiem(
    base_pkg: str,  # np. "src.modele"
    katalog: Path,  # np. Path("src")/"modele"
    zadany: str     # np. "model_wahadlo"
) -> Tuple[str, Any]:
    """
    Spróbuj załadować base_pkg.zadany; jeśli się nie uda:
    - przeszukaj dostępne pliki .py w katalogu i wybierz najlepsze dopasowanie (fuzzy),
    - w ostateczności weź pierwszy dostępny.
    Zwraca (nazwa_użyta, załadowany_moduł).
    """
    # 1) Próba bezpośrednia
    try:
        mod = dynamiczny_import(f"{base_pkg}.{zadany}", nazwa=None)
        return zadany, mod
    except Exception:
        pass

    # 2) Lista dostępnych
    dostepne = _listuj_moduly_w_katalogu(katalog)
    if not dostepne:
        raise ImportError(
            f"Brak modułów w katalogu '{katalog}'. Upewnij się, że repo ma pliki w {katalog}."
        )

    # 3) Fuzzy dopasowanie
    klucz = _znormalizuj(zadany)
    kandydaci: List[str] = []
    for n in dostepne:
        nn = _znormalizuj(n)
        if nn == klucz or klucz in nn:
            kandydaci.append(n)

    for nazwa in kandydaci + dostepne:
        try:
            mod = dynamiczny_import(f"{base_pkg}.{nazwa}", nazwa=None)
            print(f"[WARN] Nie znaleziono '{zadany}', używam '{nazwa}' z {base_pkg}. Dostępne: {dostepne}", file=sys.stderr)
            return nazwa, mod
        except Exception:
            continue

    # 4) Jeśli nic się nie udało:
    raise ImportError(
        f"Nie udało się zaimportować żadnego modułu z {base_pkg}. "
        f"Dostępne: {dostepne}. Ustaw ENV, np. MODEL={dostepne[0]}"
    )


# ---------------------------
# Główny punkt wejścia skryptu
# ---------------------------

def main() -> None:
    # Ścieżki projektu
    TU = Path(__file__).resolve()
    SRC_DIR = TU.parent
    MODELE_DIR = SRC_DIR / "modele"
    REG_DIR = SRC_DIR / "regulatory"

    # Konfiguracja z ENV
    regulator_modul = os.getenv("REGULATOR", "regulator_pid")   # np. 'regulator_pid' / 'regulator_p'
    model_modul     = os.getenv("MODEL",     "model_wahadlo")   # domyślnie było wahadło
    sciezka_cfg     = os.getenv("KONFIG",    "src/konfiguracja.json")
    wyjscie_dir     = os.getenv("WYNIKI",    "wyniki")

    # Wczytaj konfigurację
    cfg_path = Path(sciezka_cfg)
    if not cfg_path.exists():
        print(f"[WARN] Brak pliku konfiguracji: {cfg_path} – użyję pustej.", file=sys.stderr)
        konfiguracja: Dict[str, Any] = {}
    else:
        with cfg_path.open("r", encoding="utf-8") as f:
            konfiguracja = json.load(f)

    # --- Dynamiczne moduły regulatora i modelu (z fallbackiem autodetekcji) ---
    # REGULATOR
    try:
        regulator_mod, = (dynamiczny_import(f"src.regulatory.{regulator_modul}", nazwa=None),)
        wybrany_reg = regulator_modul
    except Exception:
        wybrany_reg, regulator_mod = _wybierz_modul_z_fallbackiem(
            base_pkg="src.regulatory", katalog=REG_DIR, zadany=regulator_modul
        )

    # heurystyka: bierz pierwszą klasę z modułu, której nazwa zaczyna się od "Regulator"
    RegClass = None
    for nazwa, ob in vars(regulator_mod).items():
        if inspect.isclass(ob) and nazwa.lower().startswith("regulator"):
            RegClass = ob
            break
    if RegClass is None:
        raise ImportError(f"Nie znaleziono klasy regulatora w module 'src.regulatory.{wybrany_reg}'.")

    # MODEL
    try:
        model_mod, = (dynamiczny_import(f"src.modele.{model_modul}", nazwa=None),)
        wybrany_model = model_modul
    except Exception:
        wybrany_model, model_mod = _wybierz_modul_z_fallbackiem(
            base_pkg="src.modele", katalog=MODELE_DIR, zadany=model_modul
        )

    ModelClass = None
    for nazwa, ob in vars(model_mod).items():
        if inspect.isclass(ob):
            ModelClass = ob
            break
    if ModelClass is None:
        raise ImportError(f"Nie znaleziono klasy modelu w module 'src.modele.{wybrany_model}'.")

    # --- Parametry z konfiguracji ---
    paramy_reg = konfiguracja.get("regulator", {})
    paramy_mod = konfiguracja.get("model", {})

    # Wstrzyknięcie DT z ENV (jeśli konstruktor modelu przyjmuje 'dt')
    dt_env = os.getenv("DT")
    if dt_env is not None:
        try:
            dt_val = float(dt_env)
            sig_m = inspect.signature(ModelClass.__init__)
            names = {p.name.lower() for p in sig_m.parameters.values()}
            if "dt" in names:
                paramy_mod = dict(paramy_mod)
                paramy_mod["dt"] = dt_val
        except ValueError:
            print(f"[WARN] DT='{dt_env}' nie jest liczbą – ignoruję.", file=sys.stderr)

    # --- Utworzenie instancji modelu i regulatora z mapowaniem kluczy ---
    paramy_mod_mapped = _dopasuj_kwargs_do_sygnatury(ModelClass, paramy_mod)
    model = ModelClass(**paramy_mod_mapped)

    paramy_reg_mapped = _dopasuj_kwargs_do_sygnatury(RegClass, paramy_reg)
    regulator = RegClass(**paramy_reg_mapped)

    # --- Informacyjne logi (Twoja pętla symulacyjna zostaje bez zmian) ---
    print(f"⚙️ Strojenie regulatora: {wybrany_reg}")
    print(f"[INFO] Model: {wybrany_model}")
    print(f"[INFO] Parametry regulatora (po mapowaniu): {paramy_reg_mapped}")
    print(f"[INFO] Parametry modelu (po mapowaniu):     {paramy_mod_mapped}")
    print(f"[INFO] WYNIKI -> {wyjscie_dir}")

    # TODO: tu wklej/pozostaw swoją istniejącą logikę symulacji/raportowania
    # np. pętla czasu, metryki, zapis wykresów/HTML, itp.
    # (Nie zmieniamy Twojej architektury – tylko wzmacniamy ładowanie.)
    _ = (regulator, model)  # zapobiega 'unused variable' gdy ktoś jeszcze nie wstawił pętli


if __name__ == "__main__":
    main()
