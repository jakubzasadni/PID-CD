# -*- coding: utf-8 -*-
"""
Ziegler–Nichols (closed-loop) – spójna implementacja
----------------------------------------------------
- Główna funkcja: `policz_zn(typ_regulatora, Ku, Tu)` -> dict(Kp, Ti?, Td?)
- Zwracane klucze są JEDNOLITE: "Kp", "Ti", "Td" (jeśli dotyczy).
- Dodane aliasy wstecznie kompatybilne: `strojenie_P/PI/PID`.

Uwagi:
- To klasyczne reguły ZN (oscylacje graniczne): Ku – ultimate gain, Tu – ultimate period.
- Walidacja argumentów i drobne zaokrąglenia dla stabilności raportów.
"""

from __future__ import annotations
from typing import Dict

# Mapowanie reguł ZN (closed-loop)
def _zn_p(Ku: float, Tu: float) -> Dict[str, float]:
    return {"Kp": 0.50 * Ku}

def _zn_pi(Ku: float, Tu: float) -> Dict[str, float]:
    return {"Kp": 0.45 * Ku, "Ti": Tu / 1.2}

def _zn_pid(Ku: float, Tu: float) -> Dict[str, float]:
    return {"Kp": 0.60 * Ku, "Ti": 0.50 * Tu, "Td": 0.125 * Tu}

_RULES = {
    "P": _zn_p,
    "PI": _zn_pi,
    "PID": _zn_pid,
}

def _round_out(params: Dict[str, float], ndigits: int = 10) -> Dict[str, float]:
    """Niewielkie zaokrąglenie wartości, by uniknąć szumów w raportach/JSON."""
    out: Dict[str, float] = {}
    for k, v in params.items():
        out[k] = round(float(v), ndigits)
    return out

def policz_zn(typ_regulatora: str, Ku: float, Tu: float) -> Dict[str, float]:
    """
    Policz nastawy ZN (closed-loop) dla podanego typu regulatora.

    Parameters
    ----------
    typ_regulatora : {"P","PI","PID"} (case-insensitive)
    Ku : float  (ultimate gain > 0)
    Tu : float  (ultimate period > 0)

    Returns
    -------
    Dict[str, float] : zawsze z kluczami w stylu "Kp", opcjonalnie "Ti","Td".

    Raises
    ------
    ValueError : gdy podano nieobsługiwany typ lub niepoprawne Ku/Tu.
    """
    if Ku is None or Tu is None:
        raise ValueError("policz_zn: wymagane argumenty Ku oraz Tu (oba > 0).")
    if Ku <= 0 or Tu <= 0:
        raise ValueError(f"policz_zn: Ku i Tu muszą być > 0 (otrzymano Ku={Ku}, Tu={Tu}).")

    typ_norm = str(typ_regulatora).strip().upper()
    if typ_norm not in _RULES:
        raise ValueError(f"policz_zn: nieobsługiwany typ '{typ_regulatora}'. Dozwolone: P, PI, PID.")

    params = _RULES[typ_norm](Ku, Tu)
    return _round_out(params)

# --- Aliasowe funkcje wstecznie kompatybilne (gdy ktoś ich używał wcześniej) ---

def strojenie_P(Ku: float, Tu: float) -> Dict[str, float]:
    """Alias -> policz_zn('P', Ku, Tu)."""
    return policz_zn("P", Ku, Tu)

def strojenie_PI(Ku: float, Tu: float) -> Dict[str, float]:
    """Alias -> policz_zn('PI', Ku, Tu)."""
    return policz_zn("PI", Ku, Tu)

def strojenie_PID(Ku: float, Tu: float) -> Dict[str, float]:
    """Alias -> policz_zn('PID', Ku, Tu)."""
    return policz_zn("PID", Ku, Tu)
