"""
Elastyczne przeszukiwanie siatki dla dowolnego podzbioru parametrów {Kp, Ti, Td}.
Przykład wywołania:
przeszukiwanie_siatki(
    siatki={"Kp": np.linspace(0.5,5,10), "Ti": np.linspace(5,60,10)}, 
    funkcja_celu=lambda Kp, Ti, Td=0.0: ...
)
"""

import itertools

def przeszukiwanie_siatki(siatki: dict, funkcja_celu):
    """
    :param siatki: dict z listami/iterowalnymi, np. {"Kp":[...], "Ti":[...]}.
                   Klucze opcjonalne: "Kp", "Ti", "Td".
    :param funkcja_celu: funkcja przyjmująca nazwane argumenty: Kp, Ti, Td (nieobowiązkowe).
    :return: dict {"Kp":..., "Ti":..., "Td":...} (nieobecne klucze pominięte).
    """
    keys = [k for k in ["Kp", "Ti", "Td"] if k in siatki]
    grids = [list(siatki[k]) for k in keys]

    best = None
    best_val = float("inf")

    for combo in itertools.product(*grids):
        kwargs = {k: v for k, v in zip(keys, combo)}
        # domyślne wartości gdy nie podano danego parametru
        if "Kp" not in kwargs: kwargs["Kp"] = 1.0
        if "Ti" not in kwargs: kwargs["Ti"] = 30.0
        if "Td" not in kwargs: kwargs["Td"] = 0.0

        val = funkcja_celu(**kwargs)
        if val < best_val:
            best_val = val
            best = kwargs.copy()

    # przytnij do tych, które faktycznie były w siatkach
    return {k: best[k] for k in keys}
