# Przewodnik: Testowanie workflow GitHub Actions (VERSION-7.0)

## 🎯 Cel
Przetestować nowy uproszczony workflow z pipeline v2.1 i sprawdzić:
1. ✅ Pipeline działa poprawnie (4 etapy)
2. ✅ Raport końcowy generuje się z 36 kombinacjami
3. ✅ Pass rate wynosi 75% (27/36)
4. ✅ Artefakt jest minimalistyczny (~2-3 MB zamiast 15-20 MB)

## 📋 Kroki testowania

### 1. Przejdź do Actions na GitHub
```
https://github.com/JakubZasadni/PID-CD/actions
```

### 2. Wybierz workflow
- Kliknij "Strojenie i walidacja regulatorów (Pipeline v2.1)"

### 3. Uruchom workflow manualnie
- Kliknij "Run workflow" (przycisk po prawej)
- Branch: **VERSION-7.0**
- Regulator: **all** (testowanie wszystkich 4 regulatorów)
- Kliknij "Run workflow"

### 4. Monitoruj przebieg (~3-5 minut dla "all")
#### Etapy jobу "pipeline":
```
✅ Build Docker image (~30s)
✅ Run pipeline for selected regulator(s) (~180-240s)
   - Regulator P: ~45s
   - Regulator PI: ~45s
   - Regulator PD: ~45s
   - Regulator PID: ~45s
✅ Generate comprehensive final report (~5-10s)
✅ Check results and determine status (~2s)
✅ Upload comprehensive report (~5-10s)
✅ Summary (~1s)
```

**Oczekiwany czas całkowity:** ~4-5 minut dla "all"

#### Etapy jobu "deploy" (opcjonalny):
```
✅ Download validation results (~2s)
✅ Check if deployment needed (~1s)
✅ Build Docker image (~30s)
✅ Update GitOps repository (~10-15s)
✅ Deployment summary (~1s)
```

### 5. Sprawdź logi

#### W kroku "Run pipeline for selected regulator(s)":
Szukaj:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 Pipeline dla: regulator_p
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[1/4] Strojenie metodami klasycznymi i optymalizacyjnymi...
[2/4] Walidacja wszystkich metod...
[ANALIZA] [3/4] Porównanie wyników i wybór najlepszego regulatora...
[RAPORT] [4/4] Generowanie kompleksowego raportu końcowego...
[OK] Pipeline zakończony pomyślnie
```

Powtórzone dla: `regulator_pi`, `regulator_pd`, `regulator_pid`

#### W kroku "Generate comprehensive final report":
Szukaj:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📈 Generowanie raportu końcowego (36 kombinacji)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[INFO] Zebrano X raportów rozszerzonych
[OK] Zebrano łącznie Y raportów walidacji
[INFO] Po deduplikacji: 36 unikalnych kombinacji
[OK] RAPORT KOŃCOWY WYGENEROWANY
```

#### W kroku "Check results and determine status":
Szukaj:
```
🔍 Sprawdzam wyniki walidacji...
📊 Pass rate: 75.0%
✅ Pipeline zakończony pomyślnie - pass rate: 75.0%
```

**⚠️  Jeśli zobaczysz "0% pass rate":**
- Sprawdź czy branch VERSION-7.0 ma nową konfigurację (progi walidacji)
- Sprawdź logi walidacji czy wszystkie modele zostały przetestowane

#### W kroku "Summary":
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Pipeline v2.1 zakończony
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 Pass rate: 75.0%
📁 Artefakt: raport_all
```

### 6. Pobierz artefakt

- Przewiń do dołu strony workflow run
- Znajdź sekcję "Artifacts"
- Kliknij "raport_all" aby pobrać (~2-3 MB)

### 7. Rozpakuj i sprawdź zawartość

#### Oczekiwana struktura:
```
raport_all/
├── raport_final/
│   ├── raport_koncowy.html          (~9 KB)
│   ├── raport_koncowy_dane.csv      (~4 KB)
│   ├── raport_koncowy_ranking.csv   (~1 KB)
│   ├── porownanie_IAE_boxplot.png   (~200 KB)
│   ├── porownanie_pass_rate.png     (~160 KB)
│   └── porownanie_IAE_vs_Mp.png     (~230 KB)
├── parametry_regulator_p_*.json     (3 pliki)
├── parametry_regulator_pi_*.json    (3 pliki)
├── parametry_regulator_pd_*.json    (3 pliki)
├── parametry_regulator_pid_*.json   (3 pliki)
├── najlepszy_zbiornik_1rz.json
├── najlepszy_dwa_zbiorniki.json
├── najlepszy_wahadlo_odwrocone.json
├── passed_models.txt
├── pipeline_badge.svg
└── WYNIKI_EKSPERYMENTOW.md
```

**Łącznie:** ~20 plików, ~2-3 MB

### 8. Otwórz raport końcowy

- Otwórz `raport_final/raport_koncowy.html` w przeglądarce
- Sprawdź kluczowe metryki:

#### Globalny pass rate:
```
Globalny pass rate: 75.0% (27/36)
```

#### Tabela wszystkich kombinacji:
- Powinna zawierać **36 wierszy** (4 regulatory × 3 metody × 3 modele)
- Kolumny: Regulator, Metoda, Model, IAE, Mp [%], ts [s], PASS

#### Wykresy:
- Boxplot IAE per metoda (3 metody)
- Pass rate per metoda (słupki)
- Scatter IAE vs Mp (punkty kolorowane per metoda)

#### Ranking metod:
Powinna być tabela z oceną każdej metody (Ziegler-Nichols, siatka, optymalizacja)

### 9. Sprawdź najlepsze regulatory

Otwórz pliki `najlepszy_*.json`:

```json
{
  "model": "zbiornik_1rz",
  "najlepszy_regulator": "regulator_pid",
  "metoda": "optymalizacja",
  "IAE": 5.36,
  "Mp": 5.68,
  "ts": 76.5,
  "parametry": {
    "Kp": ...,
    "Ti": ...,
    "Td": ...
  }
}
```

### 10. Sprawdź passed_models.txt

Powinien zawierać listę modeli, które przeszły walidację:
```
zbiornik_1rz
dwa_zbiorniki
wahadlo_odwrocone
```

---

## ✅ Kryteria sukcesu

### Must-have (krytyczne):
- ✅ Workflow zakończony sukcesem (zielona fajka)
- ✅ Raport końcowy wygenerowany (`raport_final/raport_koncowy.html`)
- ✅ 36 kombinacji w raporcie (nie 22!)
- ✅ Pass rate > 0% (idealnie 75%)
- ✅ Artefakt < 5 MB (powinien być ~2-3 MB)

### Should-have (ważne):
- ✅ Pass rate = 75% (27/36) - zgodnie z nowymi progami
- ✅ Wszystkie 4 regulatory przetestowane
- ✅ Wszystkie 3 modele przetestowane
- ✅ Pipeline trwa < 6 minut dla "all"

### Nice-to-have (dodatkowe):
- ✅ Job "deploy" wykonany (jeśli są passed models)
- ✅ GitOps repo zaktualizowane
- ✅ Pipeline badge wygenerowany

---

## 🐛 Możliwe problemy i rozwiązania

### Problem 1: Pass rate = 0%
**Przyczyna:** Stara konfiguracja progów  
**Rozwiązanie:** Sprawdź czy branch VERSION-7.0 ma commit z `config.yaml` (IAE_max=20, Mp_max=50, ts_max=100)

### Problem 2: Tylko 22 kombinacje zamiast 36
**Przyczyna:** Brak niektórych raportów walidacji  
**Rozwiązanie:** Sprawdź logi walidacji czy wszystkie modele zostały przetestowane

### Problem 3: Artefakt > 10 MB
**Przyczyna:** Stary workflow wciąż aktywny  
**Rozwiązanie:** Sprawdź czy plik `.github/workflows/ci.yml` został zaktualizowany

### Problem 4: Brak raportu końcowego
**Przyczyna:** Błąd w generowaniu raportu  
**Rozwiązanie:** Sprawdź logi kroku "Generate comprehensive final report"

### Problem 5: Workflow timeout
**Przyczyna:** Zbyt długie strojenie/walidacja  
**Rozwiązanie:** Sprawdź czy Docker image jest buforowany (powinien być z cache po pierwszym buildzie)

---

## 📊 Oczekiwane wyniki

### Czas wykonania (dla "all"):
- Build Docker: ~30s
- Pipeline P: ~45s
- Pipeline PI: ~45s
- Pipeline PD: ~45s
- Pipeline PID: ~45s
- Raport końcowy: ~5s
- Upload: ~5s
- **ŁĄCZNIE: ~4-5 minut**

### Rozmiar artefaktu:
- Stary workflow: 15-20 MB
- **Nowy workflow: 2-3 MB** (85% redukcja!)

### Pass rate:
- Stary workflow (22.11.2025): 0% (0/22)
- **Nowy workflow (v2.1): 75% (27/36)**

---

## 📝 Checklist testowania

- [ ] Workflow uruchomiony z opcją "all"
- [ ] Wszystkie 4 regulatory przetestowane
- [ ] Raport końcowy wygenerowany
- [ ] 36 kombinacji w raporcie
- [ ] Pass rate = 75%
- [ ] Artefakt pobrany (~2-3 MB)
- [ ] Raport HTML otwarty i sprawdzony
- [ ] Wykresy wygenerowane (3 sztuki)
- [ ] Parametry zapisane (12 plików)
- [ ] Najlepsze regulatory wybrane (3 pliki)
- [ ] Pipeline trwał < 6 minut

**Jeśli wszystkie checkboxy zaznaczone:** ✅ **Workflow działa poprawnie!**
