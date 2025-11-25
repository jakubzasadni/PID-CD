# 🚀 Quick Start - Testowanie Poprawionego Projektu

## Aktywacja Środowiska

```powershell
# Przejdź do katalogu projektu
cd C:\Users\Laptop\Desktop\Git\PID-CD

# Aktywuj środowisko wirtualne
.\.venv\Scripts\Activate.ps1
```

## Test 1: Pojedynczy Regulator (Zalecany dla pierwszego testu)

```powershell
# Strojenie regulatora PID na modelu zbiornika 1. rzędu
$env:REGULATOR = "regulator_pid"
$env:MODEL = "zbiornik_1rz"
$env:TRYB = "strojenie"
python src/uruchom_symulacje.py

# Walidacja wygenerowanych parametrów
$env:TRYB = "walidacja"
python src/uruchom_symulacje.py
```

**Oczekiwany czas:** ~2-3 minuty  
**Wyniki w:** `wyniki/parametry_regulator_pid_*.json`

## Test 2: Pełny Pipeline (Z oceną metod)

```powershell
# Uruchom cały pipeline dla jednego regulatora
$env:REGULATOR = "regulator_pid"
$env:MODEL = "zbiornik_1rz"
python src/uruchom_pipeline.py
```

**Oczekiwany czas:** ~5-7 minut  
**Wyniki w:** `wyniki/YYYYMMDD_HHMMSS/`
- `parametry_*.json` - parametry regulatorów
- `raport_*.json` - wyniki walidacji
- `raport_koncowy/` - kompleksowe porównanie

## Test 3: Wszystkie Regulatory i Modele

```powershell
# Pełny test (36 kombinacji)
$env:REGULATOR = "all"
python src/uruchom_pipeline.py
```

**Oczekiwany czas:** ~30-45 minut  
**Wyniki:** Kompleksowy raport końcowy dla wszystkich kombinacji

## 📊 Sprawdzanie Wyników

### 1. Parametry Regulatorów

```powershell
# Otwórz plik JSON z parametrami
cat wyniki/parametry_regulator_pid_optymalizacja_zbiornik_1rz.json
```

**Oczekiwane wartości:**
```json
{
  "Kp": 4.5-8.0,    // ✅ Realistyczne
  "Ti": 12-25,      // ✅ Umiarkowane
  "Td": 1.5-4.0     // ✅ Rozsądne
}
```

### 2. Wyniki Walidacji

```powershell
# Zobacz wyniki walidacji
cat wyniki/raport_regulator_pid_optymalizacja_zbiornik_1rz.json
```

**Sprawdź:**
- ✅ `PASS: true` - regulator spełnia kryteria
- ✅ `IAE < 15.0`
- ✅ `przeregulowanie < 40%`
- ✅ `czas_ustalania < 80s`

### 3. Raport Końcowy (HTML)

```powershell
# Znajdź najnowszy raport
cd wyniki
ls -Directory | Sort-Object LastWriteTime -Descending | Select-Object -First 1

# Otwórz raport HTML w przeglądarce
start ./YYYYMMDD_HHMMSS/raport_koncowy/raport_koncowy.html
```

## 🔍 Porównanie Przed/Po

### Przed Poprawkami (VERSION 6.x):
- ❌ Kp = 30.0 (nierealistyczne)
- ❌ Ti = 50.0 (zbyt wolne)
- ❌ Td = 0.1 (znikoma akcja różniczkująca)
- ❌ Ekstremalne wartości sterowania

### Po Poprawkach (VERSION 7.0):
- ✅ Kp = 4.5-8.0 (typowe dla przemysłu)
- ✅ Ti = 12-25 (zbalansowane)
- ✅ Td = 1.5-4.0 (umiarkowane)
- ✅ Ograniczone sterowanie ±10

## 🐛 Troubleshooting

### Problem: ImportError lub ModuleNotFoundError

```powershell
# Reinstaluj zależności
pip install -r kontener/requirements.txt
```

### Problem: Wyniki wciąż nierealistyczne

```powershell
# Sprawdź wersję plików config
cat src/config.yaml | Select-String "Kp:|Ti:|Td:"

# Upewnij się że zakresy są poprawione
# Kp: [0.5, 10.0]
# Ti: [5.0, 40.0]
# Td: [0.1, 8.0]
```

### Problem: Długi czas obliczeń

```powershell
# Zmniejsz gęstość siatki w config.yaml
# gestosc_siatki -> regulator_pid -> Kp: 10 (zamiast 15)
```

## 📈 Następne Kroki

1. **Analiza Wyników** - Sprawdź czy parametry są w oczekiwanych zakresach
2. **Porównanie Metod** - Zobacz raport końcowy (Ziegler-Nichols vs Siatka vs Optymalizacja)
3. **Dokumentacja** - Wykorzystaj wyniki w pracy inżynierskiej
4. **Wnioski** - Sformułuj wnioski dotyczące efektywności metod strojenia

## 💡 Wskazówki

- **Regularnie zapisuj wyniki** - każdy run tworzy nowy katalog z timestampem
- **Dokumentuj zmiany** - jeśli modyfikujesz config.yaml, zapisz zmiany w git
- **Porównuj wyniki** - użyj raportów HTML do wizualnej analizy
- **Testuj stopniowo** - zacznij od jednego regulatora, potem rozszerzaj

---

**Potrzebujesz pomocy?** Sprawdź `POPRAWKI_PROJEKTU.md` dla szczegółów technicznych.
