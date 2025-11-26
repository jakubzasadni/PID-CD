# System automatyzacji strojenia i walidacji regulatorów PID

**Wersja:** 7.0 (Poprawiona - Realistyczne Parametry) 🎯  
**Data aktualizacji:** 2025-11-25  
**Branch:** VERSION-7.0

Projekt inżynierski:
**Automatyzacja procesu strojenia, walidacji i wdrożeń aplikacji sterowania procesami w środowisku Kubernetes z wykorzystaniem narzędzi CI/CD**

---

## 🚨 WAŻNE - Wersja 7.0

**W tej wersji wprowadzono kluczowe poprawki eliminujące nierealistyczne wyniki!**

### Co zostało naprawione:
- ✅ Zakresy parametrów dostosowane do standardów przemysłowych (Kp: 0.5-10, Ti: 5-40, Td: 0.1-8)
- ✅ Ulepszona funkcja kary penalizująca ekstremalne wartości
- ✅ Dodano limity saturacji sterowania (±10)
- ✅ Zredukowano wielkości skoków i zakłóceń w testach
- ✅ Zsynchronizowano progi walidacji w całym projekcie

**Szczegóły:** Zobacz `POPRAWKI_PROJEKTU.md`  
**Quick Start:** Zobacz `QUICK_TEST.md`

---

## 🧠 Opis
System pozwala w pełni automatycznie przetestować wybrany regulator:
- wykonuje strojenie różnymi metodami,
- przeprowadza walidację na kilku modelach procesów,
- porównuje metryki jakości (IAE, ISE, przeregulowanie),
- generuje raport HTML,
- opcjonalnie może wdrożyć wynik w Kubernetes.

## ⚙️ Uruchomienie lokalne
```bash
docker build -t regulator-sim:test -f kontener/Dockerfile .
docker run --rm -e REGULATOR=regulator_pid -v ./wyniki:/app/wyniki regulator-sim:test
