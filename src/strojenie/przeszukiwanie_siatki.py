# src/strojenie/przeszukiwanie_siatki.py
import numpy as np
import itertools

def przeszukiwanie_siatki(kp_range, ti_range, metryka_funkcja):
    najlepsze = None
    min_wartosc = float("inf")

    for kp, ti in itertools.product(kp_range, ti_range):
        J = metryka_funkcja(kp, ti)
        if J < min_wartosc:
            min_wartosc = J
            najlepsze = {"kp": kp, "ti": ti}

    return najlepsze
