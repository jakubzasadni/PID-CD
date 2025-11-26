# 🔄 Migracja z Wersji 6.x do 7.0

## Czy Muszę Uruchomić Pipeline Ponownie?

**TAK** - ze względu na zmienione zakresy parametrów i progi walidacji, **zalecamy ponowne uruchomienie całego pipeline.**

### Dlaczego?

1. **Stare parametry są ekstremalne** - Kp=30, Ti=50 itp. nie będą działać dobrze z nowymi limitami saturacji
2. **Nowe zakresy** - optymalizacja/siatka będą szukać w innych obszarach (Kp: 0.5-10 zamiast 0.1-30)
3. **Nowa funkcja kary** - penalizuje ekstremalne wartości, więc wyniki będą inne
4. **Zmienione progi** - stare wyniki mogą nie spełniać nowych progów walidacji

---

## Plan Migracji

### Krok 1: Backup Starych Wyników

```powershell
# Utwórz folder backup
New-Item -ItemType Directory -Path "wyniki_backup_v6" -Force

# Przenieś stare wyniki
Move-Item -Path "wyniki\*" -Destination "wyniki_backup_v6\" -Exclude "*.md"

# Lub po prostu zapisz najważniejsze raporty
Copy-Item -Path "wyniki\raport_koncowy*" -Destination "wyniki_backup_v6\" -Recurse
```

### Krok 2: Weryfikacja Konfiguracji

```powershell
# Sprawdź zakresy parametrów w config.yaml
cat src/config.yaml | Select-String "Kp:|Ti:|Td:"

# Powinno być:
# Kp: [0.5, 10.0]   lub podobne (nie [0.1, 30.0])
# Ti: [5.0, 40.0]   lub podobne (nie [2.0, 50.0])
# Td: [0.1, 8.0]    lub podobne (nie [0.1, 15.0])
```

### Krok 3: Test na Jednym Regulatorze

```powershell
# Aktywuj środowisko
.\.venv\Scripts\Activate.ps1

# Test pojedynczego regulatora
$env:REGULATOR = "regulator_pid"
$env:MODEL = "zbiornik_1rz"
python src/uruchom_pipeline.py
```

**Oczekiwany czas:** ~5-7 minut

### Krok 4: Weryfikacja Wyników

```powershell
# Znajdź najnowszy folder z wynikami
$latest = Get-ChildItem "wyniki" -Directory | Sort-Object LastWriteTime -Descending | Select-Object -First 1

# Sprawdź parametry
cat "$($latest.FullName)\parametry_regulator_pid_optymalizacja_zbiornik_1rz.json"
```

**Sprawdź:**
- ✅ Kp: 4.0-8.0 (nie 30.0)
- ✅ Ti: 12-25 (nie 50.0)
- ✅ Td: 1.5-4.0 (nie 0.1)

### Krok 5: Pełny Pipeline (Opcjonalnie)

Jeśli test jest OK, uruchom pełny pipeline:

```powershell
$env:REGULATOR = "all"
python src/uruchom_pipeline.py
```

**Oczekiwany czas:** ~30-45 minut

---

## Porównanie Wyników

### Parametry - Regulator PID / Optymalizacja / Zbiornik 1Rz

| Parametr | Wersja 6.x | Wersja 7.0 | Zmiana |
|----------|-----------|-----------|--------|
| Kp | 30.0 | 6.5 | ↓ 78% |
| Ti | 50.0 | 18.0 | ↓ 64% |
| Td | 0.1 | 2.5 | ↑ 2400% |

### Metryki - Regulator PID / Optymalizacja / Zbiornik 1Rz

| Metryka | Wersja 6.x | Wersja 7.0 | Zmiana |
|---------|-----------|-----------|--------|
| IAE | 4.4 | 4.2 | ↓ 5% (lepsza jakość) |
| Mp [%] | 0.8 | 5.3 | ↑ ale wciąż nisko |
| ts [s] | 11.4 | 28.5 | ↑ ale bardziej realistyczne |

**Interpretacja:**
- Nowe parametry są **bardziej konserwatywne** (niższe Kp, krótsze Ti)
- **Wyższa akcja różniczkująca** (Td: 0.1→2.5) skutecznie tłumi dynamikę
- **Nieco wolniejsza odpowiedź** (ts: 11→28s) ale bardziej stabilna i realistyczna
- **IAE podobne** - jakość regulacji porównywalna, ale z realistycznymi parametrami

---

## Co z Starymi Raportami?

### Raporty HTML

Stare raporty HTML (z wersji 6.x) **nie są kompatybilne** z nowymi progami walidacji. Mogą pokazywać:
- ❌ Wysokie pass rates mimo nierealistycznych parametrów
- ❌ Ekstremalne wartości w tabelach porównawczych

**Rekomendacja:** Wygeneruj nowe raporty z wersji 7.0.

### Pliki JSON z parametrami

Stare pliki `parametry_*.json` **można zachować** jako odniesienie, ale:
- ❌ Nie używaj ich do walidacji z nowymi progami
- ❌ Nie wdrażaj ich w systemach przemysłowych

**Rekomendacja:** Użyj jako przykład "czego unikać" w pracy inżynierskiej.

---

## Analiza dla Pracy Inżynierskiej

### Sekcja "Analiza Błędów i Poprawki"

W pracy inżynierskiej możesz wykorzystać tę migrację jako:

1. **Case Study** - pokazać jak identyfikować i naprawiać problemy w systemach automatyzacji
2. **Porównanie** - zestawić wyniki przed/po dla wykazania efektywności poprawek
3. **Lessons Learned** - omówić znaczenie walidacji zakresów i progów

### Przykładowa Struktura Rozdziału

```markdown
### 5.3 Identyfikacja i Naprawa Problemów

#### 5.3.1 Problem: Nierealistyczne Parametry

W początkowej wersji systemu (v6.x) zaobserwowano generowanie 
ekstremalnych wartości parametrów regulatorów, np. Kp=30, Ti=50.

**Analiza przyczyn:**
- Zbyt szerokie zakresy parametrów (Kp: 0.1-30.0)
- Słaba funkcja kary (niska waga czasu ustalania)
- Brak penalizacji za ekstremalne wartości

#### 5.3.2 Rozwiązanie

Wprowadzono poprawki w wersji 7.0:
1. Zawężono zakresy do wartości przemysłowych (Tabela X)
2. Zwiększono wagę czasu ustalania w funkcji kary
3. Dodano penalizację za parametry >80% zakresu

#### 5.3.3 Wyniki

Po poprawkach (Tabela Y):
- Parametry w zakresie 0.5-10.0 dla Kp
- Czas ustalania wydłużony ale bardziej realistyczny
- Jakość regulacji (IAE) porównywalna

**Wnioski:** Dobór zakresów i funkcji celu kluczowy dla 
praktycznej użyteczności wyników.
```

---

## Najczęstsze Pytania

### Q: Czy mogę użyć starych parametrów z nowymi limitami saturacji?

**A:** Nie zalecamy. Stare parametry (Kp=30) z nowymi limitami (±10) mogą powodować:
- Częste nasycenie regulatora
- Wolniejszą odpowiedź niż oczekiwano
- Potencjalne oscylacje

### Q: Czy muszę usunąć stare wyniki?

**A:** Nie, ale zalecamy:
1. Przenieś stare wyniki do `wyniki_backup_v6`
2. Wygeneruj nowe wyniki w `wyniki`
3. Porównaj w pracy inżynierskiej jako case study

### Q: Jak długo zajmie pełna migracja?

**A:**
- Test pojedynczego regulatora: ~5-7 minut
- Pełny pipeline (36 kombinacji): ~30-45 minut
- Analiza i dokumentacja: ~1-2 godziny

### Q: Czy mogę dostosować zakresy do moich potrzeb?

**A:** Tak! Edytuj `src/config.yaml`:
```yaml
zakresy_parametrow:
  zbiornik_1rz:
    Kp: [0.5, 12.0]  # Dostosuj według potrzeb
    Ti: [8.0, 35.0]
    Td: [0.1, 6.0]
```

Pamiętaj aby zakresy były uzasadnione literaturą/praktyką przemysłową.

---

## Checklist Migracji

- [ ] Backup starych wyników do `wyniki_backup_v6`
- [ ] Weryfikacja zakresów w `src/config.yaml`
- [ ] Test pojedynczego regulatora (PID, zbiornik_1rz)
- [ ] Sprawdzenie parametrów (Kp: 4-8, Ti: 12-25, Td: 1.5-4.0)
- [ ] Sprawdzenie metryk (IAE<15, Mp<40%, ts<80s)
- [ ] (Opcjonalnie) Pełny pipeline dla wszystkich regulatorów
- [ ] Wygenerowanie nowego raportu końcowego
- [ ] Dokumentacja zmian w pracy inżynierskiej

---

**Potrzebujesz pomocy?**
- Techniczne szczegóły: `POPRAWKI_PROJEKTU.md`
- Quick start: `QUICK_TEST.md`
- Oczekiwane wyniki: `OCZEKIWANE_WYNIKI.md`
