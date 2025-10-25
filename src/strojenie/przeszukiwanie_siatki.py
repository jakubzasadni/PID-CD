# src/strojenie/przeszukiwanie_siatki.py
from itertools import product
from typing import Dict, Callable, Sequence

def przeszukiwanie_siatki(siatki: Dict[str, Sequence[float]], funkcja_celu: Callable):
    """
    Uniwersalne przeszukiwanie siatki po dowolnych wymiarach.
    - `siatki`: słownik {nazwa_parametru: iterowalna lista wartości}
      np. {"Kp": [...]} albo {"Kp": [...], "Ti": [...]} albo {"Kp": [...], "Ti": [...], "Td": [...]}
    - `funkcja_celu`: callable przyjmujący **te same nazwy** jako argumenty keyword-only,
      czyli np.  lambda Kp: ...  /  lambda Kp, Ti: ...  /  lambda Kp, Ti, Td: ...

    Zwraca dict najlepszych parametrów (zaokrąglonych do 2 miejsc).
    """
    if not siatki:
        raise ValueError("siatki nie może być puste")

    keys = list(siatki.keys())
    grids = [siatki[k] for k in keys]

    best_kwargs = None
    best_val = float("inf")

    for values in product(*grids):
        kwargs = {k: float(v) for k, v in zip(keys, values)}
        val = funkcja_celu(**kwargs)  # przekazujemy tylko te klucze, które istnieją
        if val < best_val:
            best_val = val
            best_kwargs = kwargs

    # Zaokrąglenie i zwrot w oryginalnych nazwach (np. "Kp","Ti","Td")
    return {k: round(v, 2) for k, v in best_kwargs.items()}
