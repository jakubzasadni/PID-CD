# 🚀 Ostatnie wdrożenie regulatorów
**Data wdrożenia:** 2025-11-06 11:04:05
## Wdrożone modele
### Zbiornik 1Rz
- **Regulator:** `regulator_pd`
- **Metoda strojenia:** `siatka`
- **Parametry:** {"regulator": "regulator_pd", "metoda": "siatka", "parametry": {"Kp": 8.0, "Ti": null, "Td": 0.1}}
- **Metryki jakości:**
  - IAE: `0.25`
  - Mp: `0.0%`
  - ts: `1.20s`
- **Status:** ✅ DEPLOYED

### Dwa Zbiorniki
- **Regulator:** `regulator_pd`
- **Metoda strojenia:** `ziegler_nichols`
- **Parametry:** {"regulator": "regulator_pd", "metoda": "ziegler_nichols", "parametry": {"Kp": 1.2, "Ti": null, "Td": 3.12}}
- **Metryki jakości:**
  - IAE: `3.06`
  - Mp: `19.3%`
  - ts: `14.65s`
- **Status:** ✅ DEPLOYED

### Wahadlo Odwrocone
- **Regulator:** `regulator_pd`
- **Metoda strojenia:** `siatka`
- **Parametry:** {"regulator": "regulator_pd", "metoda": "siatka", "parametry": {"Kp": 8.0, "Ti": null, "Td": 0.1}}
- **Metryki jakości:**
  - IAE: `0.00`
  - Mp: `0.0%`
  - ts: `0.11s`
- **Status:** ✅ DEPLOYED

