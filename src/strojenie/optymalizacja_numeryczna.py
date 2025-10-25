from typing import Sequence, Iterable, Dict, Optional
from scipy.optimize import minimize


def optymalizuj_podstawowy(
    funkcja_celu,
    x0: Sequence[float],
    granice: Optional[Sequence[tuple]] = None,
    labels: Optional[Iterable[str]] = None,
) -> Dict[str, float]:
    """
    Minimalny wrapper na scipy.optimize.minimize z obsługą etykiet zmiennych.

    - funkcja_celu: f(x) -> float
    - x0: wektor startowy (list/tuple)
    - granice: lista krotek (min, max) lub None
    - labels: nazwy zmiennych w tej samej kolejności co x0 / granice,
              np. ["Kp"], ["Kp","Ti"], ["Kp","Td"], ["Kp","Ti","Td"].

    Zwraca słownik {label_i: wartość} z zaokrągleniem do 2 miejsc.
    """
    # L-BFGS-B respektuje bounds; Nelder-Mead je ignoruje
    res = minimize(funkcja_celu, x0, bounds=granice, method="L-BFGS-B")
    x = res.x

    # Domyślne etykiety (zachowanie wstecznej kompatybilności)
    if labels is None:
        labels = []
        if len(x) >= 1: labels.append("Kp")
        if len(x) >= 2: labels.append("Ti")
        if len(x) >= 3: labels.append("Td")

    out: Dict[str, float] = {}
    for i, name in enumerate(labels):
        if i < len(x):
            out[name] = round(float(x[i]), 2)
    return out
