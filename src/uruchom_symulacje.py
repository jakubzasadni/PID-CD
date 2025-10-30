"""
Uruchamianie symulacji – wersja utwardzona:
- autodetekcja modułów (model/regulator) gdy zadany nie istnieje,
- wybór klasy Z TEGO pliku modułu (nie złapie bazowej z innego),
- mapowanie parametrów (case-insensitive, kp<->Kp, itd.),
- DT z ENV, jeśli konstruktor modelu przyjmuje 'dt',
- generowanie artefaktów do GitHub Actions:
  * wyniki/parametry_<reg>__<model>.json
  * wyniki/raport_strojenie_<reg>__<model>.html
  * wyniki/strojenie_<reg>__<model>.png
"""

from __future__ import annotations
import importlib
import inspect
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import matplotlib.pyplot as plt

try:
    from src.strojenie.ziegler_nichols import policz_zn  # opcjonalnie (fallback strojenia)
except Exception:
    policz_zn = None  # type: ignore


# Ścieżki projektu
TU = Path(__file__).resolve()
SRC_DIR = TU.parent
MODELE_DIR = SRC_DIR / "modele"
REG_DIR = SRC_DIR / "regulatory"


def uruchom_symulacje(
    regulator_modul: str = "regulator_pid",
    model_modul: str = "model_wahadlo",
    sciezka_cfg: str | Path = "src/konfiguracja.json",
    wyjscie_dir: str | Path = "wyniki"
) -> Tuple[str, str, Path, Path, Path]:
    """
    Uruchamia symulację z podanym regulatorem i modelem.
    Generuje artefakty (JSON z parametrami, wykres PNG, raport HTML).

    Args:
        regulator_modul: Nazwa modułu regulatora (bez src.regulatory.), np. "regulator_pid"
        model_modul: Nazwa modułu modelu (bez src.modele.), np. "model_wahadlo"
        sciezka_cfg: Ścieżka do pliku konfiguracji JSON
        wyjscie_dir: Katalog na wygenerowane artefakty

    Returns:
        Tuple[str, str, Path, Path, Path]: (wybrany_reg, wybrany_model, param_path, png_path, html_path)
    """
    wyjscie_dir = Path(wyjscie_dir)
    _ensure_dir(wyjscie_dir)

    cfg_path = Path(sciezka_cfg)
    if not cfg_path.exists():
        print(f"[WARN] Brak pliku konfiguracji: {cfg_path} – użyję pustej.", file=sys.stderr)
        konfiguracja: Dict[str, Any] = {}
    else:
        with cfg_path.open("r", encoding="utf-8") as f:
            konfiguracja = json.load(f)

    # --- Dynamiczne moduły regulatora i modelu (z fallbackiem autodetekcji) ---
    try:
        regulator_mod, = (dynamiczny_import(f"src.regulatory.{regulator_modul}", nazwa=None),)
        wybrany_reg = regulator_modul
    except Exception:
        wybrany_reg, regulator_mod = _wybierz_modul_z_fallbackiem("src.regulatory", REG_DIR, regulator_modul)

    # Wybieramy KLASĘ ZDEFINIOWANĄ W TYM MODULE (nie bazową z innego pliku)
    RegClass = None
    for nazwa, ob in vars(regulator_mod).items():
        if inspect.isclass(ob) and ob.__module__ == regulator_mod.__name__ and nazwa.lower().startswith("regulator"):
            RegClass = ob
            break
    if RegClass is None:
        # awaryjnie: stara heurystyka
        for nazwa, ob in vars(regulator_mod).items():
            if inspect.isclass(ob) and nazwa.lower().startswith("regulator"):
                RegClass = ob
                break
    if RegClass is None:
        raise ImportError(f"Nie znaleziono klasy regulatora w module 'src.regulatory.{wybrany_reg}'.")

    try:
        model_mod, = (dynamiczny_import(f"src.modele.{model_modul}", nazwa=None),)
        wybrany_model = model_modul
    except Exception:
        wybrany_model, model_mod = _wybierz_modul_z_fallbackiem("src.modele", MODELE_DIR, model_modul)

    # Analogicznie: klasa zdefiniowana W TYM PLIKU modułu modelu
    ModelClass = None
    for nazwa, ob in vars(model_mod).items():
        if inspect.isclass(ob) and ob.__module__ == model_mod.__name__:
            ModelClass = ob
            break
    if ModelClass is None:
        # awaryjnie: pierwsza napotkana klasa
        for nazwa, ob in vars(model_mod).items():
            if inspect.isclass(ob):
                ModelClass = ob
                break
    if ModelClass is None:
        raise ImportError(f"Nie znaleziono klasy modelu w module 'src.modele.{wybrany_model}'.")

    # --- Parametry z konfiguracji ---
    paramy_reg_cfg = konfiguracja.get("regulator", {})
    paramy_mod_cfg = konfiguracja.get("model", {})

    # DT z ENV (jeśli konstruktor modelu przyjmuje 'dt')
    dt_env = os.getenv("DT")
    if dt_env is not None:
        try:
            dt_val = float(dt_env)
            sig_m = inspect.signature(ModelClass.__init__)
            names = {p.name.lower() for p in sig_m.parameters.values()}
            if "dt" in names:
                paramy_mod_cfg = dict(paramy_mod_cfg)
                paramy_mod_cfg["dt"] = dt_val
        except ValueError:
            print(f"[WARN] DT='{dt_env}' nie jest liczbą – ignoruję.", file=sys.stderr)

    # --- Utworzenie instancji modelu i regulatora z mapowaniem kluczy ---
    paramy_mod_mapped = _dopasuj_kwargs_do_sygnatury(ModelClass, paramy_mod_cfg)

    # Najpierw zmapuj to, co przyszło z configu
    paramy_reg_mapped = _dopasuj_kwargs_do_sygnatury(RegClass, paramy_reg_cfg)

    # Jeśli nadal pusto – zastosuj fallback (ZN lub bezpieczne domyślne),
    # a POTEM PONOWNIE ZMAPUJ pod sygnaturę konstruktora.
    if not paramy_reg_mapped:
        typ = "PID"
        mlow = wybrany_reg.lower()
        if "regulator_p" in mlow and "pid" not in mlow and "pi" not in mlow and "pd" not in mlow:
            typ = "P"
        elif "regulator_pi" in mlow:
            typ = "PI"
        elif "regulator_pd" in mlow:
            typ = "PD"
        elif "regulator_pid" in mlow:
            typ = "PID"

        fallback_params: Dict[str, Any] = {}
        if policz_zn is not None and typ in ("P", "PI", "PID"):
            fallback_params = policz_zn(typ, Ku=2.0, Tu=25.0)  # placeholder Ku/Tu
        else:
            # ostrożne domyślne
            sig_r = inspect.signature(RegClass.__init__)
            rp = sig_r.parameters
            if "Kp" in rp or "kp" in rp:
                fallback_params["Kp"] = 1.0
            if "Ti" in rp or "ti" in rp:
                fallback_params.setdefault("Ti", 1.0)
            if "Td" in rp or "td" in rp:
                fallback_params.setdefault("Td", 0.0)

        # KLUCZOWE: ponownie mapujemy fallback na sygnaturę konstruktora (Kp→kp itd.)
        paramy_reg_mapped = _dopasuj_kwargs_do_sygnatury(RegClass, fallback_params)

    model = ModelClass(**paramy_mod_mapped)
    regulator = RegClass(**paramy_reg_mapped)

    # --- Informacyjne logi ---
    print(f"⚙️ Strojenie regulatora: {wybrany_reg}")
    print(f"[INFO] Model: {wybrany_model}")
    print(f"[INFO] Parametry regulatora (po mapowaniu): {paramy_reg_mapped}")
    print(f"[INFO] Parametry modelu (po mapowaniu):     {paramy_mod_mapped}")
    print(f"[INFO] WYNIKI -> {wyjscie_dir}")

    # ------------------------------------------
    # (A) TU możesz wkleić swoją właściwą symulację
    # ------------------------------------------
    # Placeholder: prosta odpowiedź 1-rz. na skok (żeby były artefakty)
    t_end = 10.0
    dt = float(paramy_mod_mapped.get("dt", 0.01))
    t = np.arange(0.0, t_end + dt, dt)
    u = np.ones_like(t)
    tau = 2.0
    y = 1.0 - np.exp(-t / tau)

    # --- Zapis artefaktów (nazwy zgodne z patternem uploadu) ---
    base = f"{_slug(wybrany_reg)}__{_slug(wybrany_model)}"
    param_path = _zapisz_parametry_json(wyjscie_dir, base, wybrany_reg, wybrany_model,
                                        paramy_reg_mapped, paramy_mod_mapped)
    png_path = _zapisz_wykres_png(wyjscie_dir, base, t, y, u)
    html_path = _zapisz_html(wyjscie_dir, base, png_path.name, param_path.name)

    return wybrany_reg, wybrany_model, param_path, png_path, html_path


# ---------------------------------------
# Pomocnicze: bezpieczny dynamiczny import
# ---------------------------------------

def dynamiczny_import(modul: str, nazwa: str | None = None) -> Any:
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
        # 1) znane synonimy (kp->Kp)
        if low in _SYNONIMY:
            cel = _SYNONIMY[low]
            if cel in akceptowane:
                wynik[cel] = v
                continue
        # 2) bezpośrednie dopasowanie (case-insensitive) do parametrów __init__
        if low in akceptowane_low:
            wynik[akceptowane_low[low]] = v
            continue
        # brak dopasowania → ignorujemy
    return wynik


# ---------------------------------------------------
# Autodetekcja nazw modułów w repo (bez zmiany struktury)
# ---------------------------------------------------

def _listuj_moduly_w_katalogu(katalog: Path) -> List[str]:
    if not katalog.exists():
        return []
    return sorted([p.stem for p in katalog.glob("*.py") if p.name != "__init__.py"])

def _znormalizuj(nazwa: str) -> str:
    return nazwa.lower().replace("_", "").replace("-", "")

def _wybierz_modul_z_fallbackiem(base_pkg: str, katalog: Path, zadany: str) -> Tuple[str, Any]:
    # 1) próba bezpośrednia
    try:
        mod = dynamiczny_import(f"{base_pkg}.{zadany}", nazwa=None)
        return zadany, mod
    except Exception:
        pass

    # 2) lista dostępnych
    dostepne = _listuj_moduly_w_katalogu(katalog)
    if not dostepne:
        raise ImportError(f"Brak modułów w katalogu '{katalog}'.")

    # 3) fuzzy dopasowanie
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

    raise ImportError(f"Nie udało się zaimportować żadnego modułu z {base_pkg}. Dostępne: {dostepne}.")


# ---------------------------
# Zapisywanie artefaktów
# ---------------------------

def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)

def _slug(s: str) -> str:
    return s.replace("/", "_").replace("\\", "_").replace(" ", "_")

def _zapisz_parametry_json(dst_dir: Path, base: str, reg: str, model: str,
                           param_reg: Dict[str, Any], param_mod: Dict[str, Any]) -> Path:
    out = {
        "regulator": reg,
        "model": model,
        "parametry_regulatora": param_reg,
        "parametry_modelu": param_mod,
    }
    p = dst_dir / f"parametry_{base}.json"
    with p.open("w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    return p

def _zapisz_wykres_png(dst_dir: Path, base: str, t: np.ndarray, y: np.ndarray, u: np.ndarray) -> Path:
    p = dst_dir / f"strojenie_{base}.png"
    plt.figure()
    plt.plot(t, y, label="y(t)")
    plt.plot(t, u, label="u(t)")
    plt.xlabel("t")
    plt.ylabel("wartość")
    plt.title(f"Strojenie: {base}")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(p)
    plt.close()
    return p

def _zapisz_html(dst_dir: Path, base: str, png_name: str, param_json_name: str) -> Path:
    p = dst_dir / f"raport_strojenie_{base}.html"
    html = f"""<!doctype html>
<html lang="pl">
<head><meta charset="utf-8"><title>Raport strojenia – {base}</title></head>
<body>
  <h1>Raport strojenia – {base}</h1>
  <p>Parametry: <code>{param_json_name}</code></p>
  <img src="{png_name}" alt="Wykres strojenia" style="max-width:100%;height:auto;"/>
</body>
</html>
"""
    p.write_text(html, encoding="utf-8")
    return p


# ---------------------------------------------
# Bezpośrednie uruchomienie → ENV lub domyślne
# ---------------------------------------------

def main() -> None:
    """
    Główna funkcja do uruchamiania symulacji bezpośrednio (skrypt).
    Wspiera autodetekcję modułów, gdy zadany nie istnieje.
    """
    regulator_modul = os.getenv("REGULATOR", "regulator_pid")
    model_modul     = os.getenv("MODEL",     "model_wahadlo")
    sciezka_cfg     = os.getenv("KONFIG",    "src/konfiguracja.json")
    wyjscie_dir     = os.getenv("WYNIKI",    "wyniki")

    uruchom_symulacje(
        regulator_modul=regulator_modul,
        model_modul=model_modul,
        sciezka_cfg=sciezka_cfg,
        wyjscie_dir=wyjscie_dir
    )


if __name__ == "__main__":
    main()