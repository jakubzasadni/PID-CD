# src/strojenie/ziegler_nichols.py
"""
Ziegler–Nichols: strojenie regulatora PID/PI na podstawie oscylacji granicznych.
"""
def strojenie_PID(Ku, Tu):
    return {"kp": 0.6 * Ku, "ti": 0.5 * Tu, "td": 0.125 * Tu}

def strojenie_PI(Ku, Tu):
    return {"kp": 0.45 * Ku, "ti": 0.83 * Tu}
"""
Ziegler–Nichols: strojenie regulatora PID/PI na podstawie oscylacji granicznych.
Zwraca parametry w ujednoliconym formacie {"Kp", "Ti", "Td"}.
"""

def strojenie_PID(Ku, Tu):
    return {
        "Kp": round(0.6 * Ku, 4),
        "Ti": round(0.5 * Tu, 4),
        "Td": round(0.125 * Tu, 4)
    }

def strojenie_PI(Ku, Tu):
    return {
        "Kp": round(0.45 * Ku, 4),
        "Ti": round(0.83 * Tu, 4),
        "Td": 0.0
    }

def strojenie_P(Ku):
    """
    Prosty wariant P — tylko wzmocnienie proporcjonalne.
    """
    return {
        "Kp": round(0.5 * Ku, 4),
        "Ti": 0.0,
        "Td": 0.0
    }
