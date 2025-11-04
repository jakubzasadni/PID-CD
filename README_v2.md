# System automatyzacji strojenia i walidacji regulatorów

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
