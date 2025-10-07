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

## ⚙️ Uruchomienie lokalne
```bash
docker build -t regulator-sim:test -f kontener/Dockerfile .
docker run --rm -e REGULATOR=regulator_pid -v ./wyniki:/app/wyniki regulator-sim:test
