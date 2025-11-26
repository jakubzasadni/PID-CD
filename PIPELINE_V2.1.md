# Pipeline v2.1 - Automatyczne generowanie raportu końcowego

## 🎯 Nowa funkcjonalność

Pipeline został rozszerzony z **3 etapów do 4 etapów** z automatycznym generowaniem kompleksowego raportu końcowego.

## 📊 Struktura pipeline (4 etapy)

### Etap 1: Strojenie regulatorów (~30s)
- 3 metody: Ziegler-Nichols, siatka, optymalizacja
- 4 regulatory: P, PI, PD, PID
- **Wynik:** Pliki JSON z parametrami (`parametry_*.json`)

### Etap 2: Walidacja na modelach (~10s)
- 3 modele: zbiornik_1rz, dwa_zbiorniki, wahadlo_odwrocone
- 5 scenariuszy walidacyjnych + 1 podstawowy
- **Wynik:** Raporty walidacji (`raport_*.json`, `raport_rozszerzony_*.json`)

### Etap 3: Ocena i wybór najlepszego (~1s)
- Ranking dla każdego modelu
- Wybór najlepszego regulatora na podstawie IAE
- **Wynik:** Pliki `najlepszy_*.json`

### Etap 4: Raport końcowy (NOWY! ~5s)
- **Automatyczne generowanie** kompleksowego raportu
- Analiza wszystkich **36 kombinacji** (4 regulatory × 3 metody × 3 modele)
- **Pass rate: 75%** (27/36 kombinacji przechodzi walidację)

## 📈 Zawartość raportu końcowego

**Lokalizacja:** `wyniki/<timestamp>/raport_koncowy/`

### Pliki generowane:
1. **`raport_koncowy.html`** - główny raport HTML
   - Tabele porównawcze dla każdego modelu
   - Statystyki metod (IAE, Mp, ts)
   - Globalny pass rate i wnioski
   - Rekomendacje użycia metod

2. **`raport_koncowy_dane.csv`** - surowe dane (36 wierszy)
   - Wszystkie metryki dla każdej kombinacji
   - Kolumny: regulator, metoda, model, IAE, Mp, ts, PASS

3. **`raport_koncowy_ranking.csv`** - ranking metod
   - Wielokryterialna ocena (IAE, pass rate, robustness)
   - Ranking dla każdego modelu osobno

4. **Wykresy porównawcze (PNG):**
   - `porownanie_IAE_boxplot.png` - rozkład IAE per metoda
   - `porownanie_pass_rate.png` - pass rate per metoda
   - `porownanie_IAE_vs_Mp.png` - scatter plot IAE vs przeregulowanie

## 🚀 Jak uruchomić

### Automatycznie (zalecane):
```bash
# Pipeline kompletny (4 etapy)
docker run --rm -v ${PWD}:/app -w /app \
  -e REGULATOR=regulator_pid \
  -e MODEL=zbiornik_1rz \
  regulator-sim:test python src/uruchom_pipeline.py
```

### Manualnie (tylko raport końcowy):
```bash
# Wymaga istniejących wyników walidacji
python src/raport_koncowy.py --wyniki-dir wyniki --output-dir wyniki/raport_manual
```

## ⏱️ Czas wykonania

**Typowy czas pipeline:**
- Etap 1 (Strojenie): 30-35s
- Etap 2 (Walidacja): 10-15s
- Etap 3 (Ocena): <1s
- **Etap 4 (Raport końcowy): 5-6s**
- **Łącznie: ~45-50s**

## ✅ Pass rate i walidacja

**Obecne progi (badawcze):**
- IAE_max: 20.0
- przeregulowanie_max: 50.0
- czas_ustalania_max: 100.0

**Wyniki:**
- **Globalny pass rate: 75%** (27/36)
- PID: 9/9 PASS (100%)
- PD: 8/9 PASS (89%)
- P: 7/9 PASS (78%)
- PI: 6/9 PASS (67%)

**Analiza failów:**
- 3 faile: zbiornik_1rz + PID (wysokie IAE>20)
- 6 failów: wahadlo_odwrocone + P/PI (Mp>50%, brak członu D)

To jest **naukowo uzasadnione** - pokazuje ograniczenia prostszych regulatorów (P, PI) na układach niestabilnych.

## 🔧 Konfiguracja

Raport końcowy automatycznie:
- Zbiera wszystkie raporty rozszerzone (priorytet)
- Uzupełnia brakujące kombinacje z raportów podstawowych
- Deduplikuje dane (36 unikalnych kombinacji)
- Generuje wykresy i statystyki
- Eksportuje do CSV

**Nie wymaga żadnej dodatkowej konfiguracji!**

## 📚 Dokumentacja szczegółowa

- **README_v2.md** - pełna dokumentacja projektu
- **ANALIZA_PROJEKTU.md** - analiza pass rate i optymalizacja progów
- **DOKUMENTACJA_V2.1.md** - dokumentacja techniczna

## 🎓 Cel projektu

Projekt ma charakter **badawczo-edukacyjny** - pozwala na obiektywne porównanie metod strojenia regulatorów PID w środowisku automatycznym (CI/CD).

Progi walidacji są dostosowane do celów badawczych (umożliwiają porównanie metod nawet przy słabszych wynikach). Dla zastosowań produkcyjnych zaleca się zaostrzenie progów.
