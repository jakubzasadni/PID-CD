# src/strojenie/ziegler_nichols.py
def strojenie_ZN(RegulatorClass, model_nazwa, typ_regulatora):
    if model_nazwa == "zbiornik_1rz":
        Ku, Tu = 10.0, 20.0
    elif model_nazwa == "dwa_zbiorniki":
        Ku, Tu = 5.0, 30.0
    elif model_nazwa == "wahadlo_odwrocone":
        Ku, Tu = 15.0, 4.0
    else:
        Ku, Tu = 8.0, 20.0
    
    print(f"[ZN] Uzywam Ku={Ku}, Tu={Tu} dla modelu {model_nazwa}")
    
    typ = typ_regulatora.lower()
    if typ == "regulator_p":
        return {"Kp": round(0.5 * Ku, 4), "Ti": None, "Td": None}
    elif typ == "regulator_pi":
        return {"Kp": round(0.45 * Ku, 4), "Ti": round(0.83 * Tu, 4), "Td": None}
    elif typ == "regulator_pd":
        return {"Kp": round(0.6 * Ku, 4), "Ti": None, "Td": round(0.125 * Tu, 4)}
    else:
        return {"Kp": round(0.6 * Ku, 4), "Ti": round(0.5 * Tu, 4), "Td": round(0.125 * Tu, 4)}
