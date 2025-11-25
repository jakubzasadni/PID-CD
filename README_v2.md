# System automatyzacji strojenia i walidacji regulatorów

![Pipeline Time](wyniki/pipeline_badge.svg)

Projekt inżynierski:
**Automatyzacja procesu strojenia, walidacji i wdrożeń aplikacji sterowania procesami w środowisku Kubernetes z wykorzystaniem narzędzi CI/CD**

## 🧠 Opis

**Cel projektu:** Badawczo-edukacyjny system do automatycznego porównania metod strojenia regulatorów PID.

System pozwala w pełni automatycznie przetestować wybrany regulator:
- wykonuje strojenie **trzema metodami** (Ziegler-Nichols, Przeszukiwanie siatki, Optymalizacja numeryczna),
- przeprowadza walidację na **trzech modelach** procesów (zbiornik I rzędu, II rzędu, wahadło odwrocone),
- porównuje **cztery typy regulatorów** (P, PI, PD, PID),
- analizuje metryki jakości (IAE, ISE, przeregulowanie, czas ustalania),
- generuje **profesjonalny raport HTML** z wykresami i wnioskami,
- opcjonalnie może wdrożyć wynik w Kubernetes przez GitOps.

**Uwaga:** Progi walidacji (`IAE_max`, `przeregulowanie_max`, `czas_ustalania_max`) są dostosowane do **celów badawczych** - pozwalają na przejście większości kombinacji i porównanie metod. Dla zastosowań produkcyjnych należy je zmniejszyć.

Nowości w wersji 2.0:
- konfigurowalne zakresy parametrów i wagi funkcji kary w `src/config.yaml`,
- równoległe i adaptacyjne przeszukiwanie siatki (2 fazy: gruba → zagęszczenie),
- optymalizacja numeryczna z multi-start (w tym start z Ziegler–Nichols),
- rozszerzona walidacja (wiele scenariuszy: różne skoki r, zakłócenia, szum),
- raporty porównawcze metod strojenia (HTML + wykresy),
- logowanie do pliku `wyniki/strojenie.log` i paski postępu.

**Nowości w wersji 2.1 (CI/CD Enhanced):**
- 📊 **Metryki pipeline** - automatyczny pomiar czasu każdego etapu (4 etapy)
- 📈 **Raport końcowy** - profesjonalne porównanie wszystkich 36 kombinacji (HTML + CSV + wykresy)
- 🚀 **Automatyczne wdrożenie GitOps** - aktualizacja ConfigMap w Kubernetes po walidacji
- 📉 **Historia eksperymentów** - tracking wszystkich uruchomień pipeline
- ⏱️ **Badge czasu pipeline** - wizualizacja wydajności CI/CD
- ✅ **75% pass rate** - zoptymalizowane progi walidacji dla celów badawczych

**Pipeline składa się z 4 etapów:**
1. **Strojenie** - 3 metody (Ziegler-Nichols, siatka, optymalizacja) × 4 regulatory
2. **Walidacja** - testy na 3 modelach (zbiornik_1rz, dwa_zbiorniki, wahadlo_odwrocone)
3. **Ocena** - wybór najlepszego regulatora dla każdego modelu
4. **Raport końcowy** - kompleksowa analiza wszystkich 36 kombinacji (regulator × metoda × model)

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

### Plik: `src/config.yaml`

**Kluczowe sekcje:**
- `zakresy_parametrow` – zakresy Kp/Ti/Td (globalne i per model)
- `gestosc_siatki` – liczba punktów siatki dla P/PI/PD/PID
- `adaptacyjne_przeszukiwanie` – włączenie i parametry 2-fazowego przeszukiwania
- `optymalizacja` – liczba startów, metoda, maxiter
- `wagi_kary` – wagi przeregulowania (0.3) i czasu ustalania (0.05); kara za stałe u
- `walidacja` – lista 5 scenariuszy + **progi akceptacji**
- `raportowanie` – format, DPI, flagi

### ⚙️ Progi walidacji (v2.1)

**Aktualne (badawcze):**
```yaml
IAE_max: 20.0              # Realistyczne dla różnych modeli
przeregulowanie_max: 50.0  # Akceptowalne dla układów niestabilnych (wahadło)
czas_ustalania_max: 100.0  # Wystarczające dla układów II rzędu
```

**Uzasadnienie:**
- Zbiornik II rzędu (dwa_zbiorniki) naturalnie potrzebuje 60-80s na ustalenie
- Wahadło odwrocone ma przeregulowanie 50-100% przy stabilizacji (układ niestabilny)
- IAE=20 pozwala na porównanie metod nawet przy słabszych parametrach

**Dla zastosowań produkcyjnych** zmień na:
```yaml
IAE_max: 15.0
przeregulowanie_max: 35.0
czas_ustalania_max: 75.0
```

## 🎯 Narzędzia i raporty (v2.1)

### 1. Pipeline kompletny (automatyczny)
Uruchamia pełny cykl: strojenie → walidacja → ocena → raport końcowy
```bash
# Docker
docker run --rm -v ${PWD}:/app -w /app \
  -e REGULATOR=regulator_pid \
  -e MODEL=zbiornik_1rz \
  regulator-sim:test python src/uruchom_pipeline.py

# Python lokalnie
python src/uruchom_pipeline.py
```

**Wyniki automatyczne:**
- `wyniki/<timestamp>/raport_koncowy/` - raport końcowy z 36 kombinacjami
  - `raport_koncowy.html` - kompletny raport HTML (75% pass rate)
  - `raport_koncowy_dane.csv` - wszystkie metryki
  - `raport_koncowy_ranking.csv` - ranking metod
  - `porownanie_*.png` - wykresy porównawcze (IAE boxplot, pass rate, IAE vs Mp)
- `wyniki/pipeline_badge.svg` - badge z czasem pipeline
- `wyniki/WYNIKI_EKSPERYMENTOW.md` - raport markdown z historią

### 2. Raport końcowy (manualny)
Generuje raport z już istniejących wyników:
```powershell
python src/raport_koncowy.py --wyniki-dir wyniki
```
### 2. Raport końcowy (manualny)
Generuje raport z już istniejących wyników:
```powershell
python src/raport_koncowy.py --wyniki-dir wyniki
```
**Zawiera:**
- Tabele porównawcze dla każdego modelu
- Wykresy pudełkowe (boxplot) IAE
- Wykresy pass rate i IAE vs Mp
- Ranking metod (wielokryterialna ocena)
- Eksport danych do CSV
- Automatyczne wnioski i rekomendacje

**Uwaga:** Pipeline automatycznie generuje ten raport w etapie 4/4.

### 3. Automatyczne wdrożenie GitOps
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

**Lokalne wdrożenie Kubernetes:**
Repository GitOps zawiera kompletne narzędzia do lokalnego wdrożenia z ArgoCD. Zobacz:
📦 [cl-gitops-regulatory/LOCAL_DEPLOYMENT.md](https://github.com/JakubZasadni/cl-gitops-regulatory/blob/main/LOCAL_DEPLOYMENT.md)

### 4. Metryki CI/CD Pipeline
Automatyczny pomiar czasu i generowanie raportów:
```powershell
# Metryki są automatycznie zbierane podczas uruchomienia pipeline (4 etapy)
python src/uruchom_pipeline.py
```
**Generowane pliki:**
- `wyniki/pipeline_metrics.json` - metryki ostatniego uruchomienia
- `wyniki/pipeline_history.json` - historia 50 ostatnich runów
- `wyniki/pipeline_badge.svg` - badge z czasem pipeline
- `wyniki/WYNIKI_EKSPERYMENTOW.md` - raport markdown z porównaniem do manualnego strojenia

**Przykładowy czas pipeline:**
- Etap 1 (Strojenie): ~30s
- Etap 2 (Walidacja): ~10s
- Etap 3 (Ocena): <1s
- Etap 4 (Raport końcowy): ~5s
- **Łącznie:** ~45-50s

**Zobacz raport:**
```powershell
cat wyniki/WYNIKI_EKSPERYMENTOW.md
```

## 🚀 Wdrożenie lokalne z Kubernetes + ArgoCD

System umożliwia pełne lokalne wdrożenie w klastrze Minikube z automatyczną synchronizacją przez ArgoCD.

**Szybki start:**
```powershell
# Sklonuj repo GitOps
git clone https://github.com/JakubZasadni/cl-gitops-regulatory.git
cd cl-gitops-regulatory

# Automatyczna instalacja (Minikube + ArgoCD + Aplikacje)
./install-local.ps1

# Dostęp do ArgoCD UI
./start-argocd-ui.ps1

# Status środowiska
./status.ps1
```

**Co zostanie wdrożone:**
- ✅ Klaster Kubernetes (Minikube)
- ✅ ArgoCD (GitOps controller)
- ✅ 3 aplikacje regulatorów:
  - `dwa-zbiorniki`
  - `wahadlo-odwrocone`
  - `zbiornik-1rz`

**Automatyczna synchronizacja:**
1. Pipeline CI/CD w `PID-CD` generuje nowe parametry
2. Automatycznie commituje do `cl-gitops-regulatory`
3. ArgoCD wykrywa zmiany i wdraża do klastra
4. Aplikacje są automatycznie aktualizowane

**Pełna dokumentacja:**
📖 [LOCAL_DEPLOYMENT.md](https://github.com/JakubZasadni/cl-gitops-regulatory/blob/main/LOCAL_DEPLOYMENT.md)

