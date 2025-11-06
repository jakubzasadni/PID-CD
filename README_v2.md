# System automatyzacji strojenia i walidacji regulatorów

![Pipeline Time](wyniki/pipeline_badge.svg)

Projekt inżynierski:
**Automatyzacja procesu strojenia, walidacji i wdrożeń aplikacji sterowania procesami w środowisku Kubernetes z wykorzystaniem narzędzi CI/CD**

## 🧠 Opis
System pozwala w pełni automatycznie przetestować wybrany regulator:
- wykonuje strojenie różnymi metodami,
- przeprowadza walidację na kilku modelach procesów,
- porównuje metryki jakości (IAE, ISE, przeregulowanie),
- generuje raport HTML,
- opcjonalnie może wdrożyć wynik w Kubernetes.

Nowości w wersji 2.0:
- konfigurowalne zakresy parametrów i wagi funkcji kary w `src/config.yaml`,
- równoległe i adaptacyjne przeszukiwanie siatki (2 fazy: gruba → zagęszczenie),
- optymalizacja numeryczna z multi-start (w tym start z Ziegler–Nichols),
- rozszerzona walidacja (wiele scenariuszy: różne skoki r, zakłócenia, szum),
- raporty porównawcze metod strojenia (HTML + wykresy),
- logowanie do pliku `wyniki/strojenie.log` i paski postępu.

**Nowości w wersji 2.1 (CI/CD Enhanced):**
- 📊 **Metryki pipeline** - automatyczny pomiar czasu każdego etapu
- 📈 **Raport końcowy** - profesjonalne porównanie wszystkich metod (HTML + CSV + wykresy)
- 🚀 **Automatyczne wdrożenie GitOps** - aktualizacja ConfigMap w Kubernetes po walidacji
- 📉 **Historia eksperymentów** - tracking wszystkich uruchomień pipeline
- ⏱️ **Badge czasu pipeline** - wizualizacja wydajności CI/CD

## ⚙️ Uruchomienie lokalne (Docker)
```bash
docker build -t regulator-sim:test -f kontener/Dockerfile .
# Strojenie jednego regulatora i modelu
docker run --rm -e PYTHONPATH=/app -e TRYB=strojenie -e REGULATOR=regulator_pid -e MODEL=zbiornik_1rz -v ./wyniki:/app/wyniki regulator-sim:test
# Walidacja + raporty porównawcze
docker run --rm -e PYTHONPATH=/app -e TRYB=walidacja -e REGULATOR=regulator_pid -e MODEL=zbiornik_1rz -v ./wyniki:/app/wyniki regulator-sim:test
```

## ⚙️ Uruchomienie lokalne (Python)
```powershell
# W katalogu projektu
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r kontener/requirements.txt

# Ustaw PYTHONPATH, uruchom strojenie
$env:PYTHONPATH = (Get-Location).Path
$env:TRYB = "strojenie"; $env:REGULATOR = "regulator_pid"; $env:MODEL = "zbiornik_1rz"
python src/uruchom_symulacje.py

# Walidacja i raporty
$env:TRYB = "walidacja"
python src/uruchom_symulacje.py
```

## 🧾 Konfiguracja
- Plik: `src/config.yaml`
- Kluczowe sekcje:
  - `zakresy_parametrow` – zakresy Kp/Ti/Td (globalne i per model),
  - `gestosc_siatki` – liczba punktów siatki dla P/PI/PD/PID,
  - `adaptacyjne_przeszukiwanie` – włączenie i parametry 2-fazowego przeszukiwania,
  - `optymalizacja` – liczba startów, metoda, maxiter,
  - `wagi_kary` – wagi przeregulowania i czasu ustalania; kara za stałe u,
  - `walidacja` – lista scenariuszy + progi,
  - `raportowanie` – format, DPI, flagi.

## 🎯 Nowe narzędzia (v2.1)

### 1. Raport końcowy porównawczy
Generuje profesjonalny raport HTML z porównaniem wszystkich metod:
```powershell
python src/raport_koncowy.py --wyniki-dir wyniki
```
**Zawiera:**
- Tabele porównawcze dla każdego modelu
- Wykresy pudełkowe (boxplot) IAE
- Heatmapa czasu obliczeń
- Ranking metod (wielokryterialna ocena)
- Eksport danych do CSV
- Automatyczne wnioski i rekomendacje

**Wyniki:** `wyniki/raport_koncowy_<timestamp>/`

### 2. Automatyczne wdrożenie GitOps
Wdraża najlepsze parametry do Kubernetes przez GitOps:
```powershell
python src/wdrozenie_gitops.py --gitops-repo ../cl-gitops-regulatory
```
**Funkcje:**
- Wybiera najlepsze parametry na podstawie IAE
- Tworzy/aktualizuje ConfigMapy
- Dodaje adnotacje z metrykami do deploymentów
- Commituje zmiany z opisem
- (Opcjonalnie) Push do remote

**Opcje:**
- `--no-commit` - tylko aktualizuj pliki bez commitu
- `--push` - automatyczny push do remote
- `--model zbiornik_1rz` - wdróż tylko konkretny model

### 3. Metryki CI/CD Pipeline
Automatyczny pomiar czasu i generowanie raportów:
```powershell
# Metryki są automatycznie zbierane podczas uruchomienia pipeline
python src/uruchom_pipeline.py
```
**Generowane pliki:**
- `wyniki/pipeline_metrics.json` - metryki ostatniego uruchomienia
- `wyniki/pipeline_history.json` - historia 50 ostatnich runów
- `wyniki/pipeline_badge.svg` - badge z czasem pipeline
- `wyniki/WYNIKI_EKSPERYMENTOW.md` - raport markdown z porównaniem do manualnego strojenia

**Zobacz raport:**
```powershell
cat wyniki/WYNIKI_EKSPERYMENTOW.md
```
