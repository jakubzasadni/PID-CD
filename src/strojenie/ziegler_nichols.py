# src/strojenie/ziegler_nichols.py
"""
Ziegler–Nichols: strojenie regulatora PID/PI na podstawie oscylacji granicznych.
"""
def strojenie_PID(Ku, Tu):
    return {"kp": 0.6 * Ku, "ti": 0.5 * Tu, "td": 0.125 * Tu}

def strojenie_PI(Ku, Tu):
    return {"kp": 0.45 * Ku, "ti": 0.83 * Tu}
