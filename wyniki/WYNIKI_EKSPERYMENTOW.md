# Wyniki eksperymentów CI/CD
**Ostatnia aktualizacja:** 2025-11-26 21:17:55
![Pipeline Time](pipeline_badge.svg)
## Statystyki pipeline
- **Całkowita liczba uruchomień:** 2
- **Udane uruchomienia:** 2 (100.0%)
- **Nieudane uruchomienia:** 0
- **Średni czas wykonania:** 0:00:24
- **Najszybszy run:** 0:00:01
- **Najwolniejszy run:** 0:00:47

## Ostatnie uruchomienie
- **Status:** [OK] SUCCESS
- **Data:** 2025-11-25T18:49:08.020301
- **Czas trwania:** 0:00:47

### Czasy etapów
| Etap | Czas | Status |
|------|------|--------|
| Strojenie regulatorów | 31.5s | [OK] success |
| Walidacja na modelach | 11.11s | [OK] success |
| Ocena i porównanie metod | 0.03s | [OK] success |
| Generowanie raportu końcowego | 5.3s | [OK] success |

## Porównanie: Automatyczne vs Manualne strojenie
| Aspekt | Manualne strojenie | CI/CD Pipeline | Oszczędność |
|--------|-------------------|----------------|-------------|
| Czas (godz) | ~18.0h | ~0.0h | 18.0h (100%) |
| Powtarzalność | Niska | Wysoka | [OK] |
| Błądy ludzkie | Możliwe | Wyeliminowane | [OK] |
| Dokumentacja | Manualna | Automatyczna | [OK] |
| Wdrożenie | Manualne | Automatyczne (GitOps) | [OK] |

## Historia ostatnich 10 uruchomień
| # | Data | Status | Czas | Etapy OK |
|---|------|--------|------|----------|
| 1 | 2025-11-25 | [OK] | 48s | 4/4 |
| 2 | 2025-11-06 | [OK] | 2s | 3/3 |

---
*Raport generowany automatycznie przez `src/metryki_pipeline.py`*
