# 🚀 Quick Start - Nowe funkcje v2.1

## Dla pracy inżynierskiej - 3 nowe narzędzia

### 1️⃣ Raport końcowy porównawczy (5 minut)

**Uruchom po zakończeniu eksperymentów:**
```powershell
python src/raport_koncowy.py
```

**Co otrzymasz:**
- 📄 `wyniki/raport_koncowy_<timestamp>/raport_koncowy.html` - **OTWÓRZ W PRZEGLĄDARCE**
- 📊 4 wykresy profesjonalne (gotowe do pracy!)
- 📈 Tabele porównawcze dla każdego modelu
- 🏆 Ranking metod strojenia
- 💾 Dane CSV do Excel/Python

**Wklej do pracy:**
- Tabele → Rozdział "Wyniki"
- Wykresy → Aneks A
- Ranking → Rozdział "Porównanie metod"

---

### 2️⃣ Metryki CI/CD (automatyczne!)

**Uruchom pipeline z metrykami:**
```powershell
python src/uruchom_pipeline.py
```

**Co otrzymasz automatycznie:**
- ⏱️ `wyniki/pipeline_badge.svg` - badge do README
- 📊 `wyniki/WYNIKI_EKSPERYMENTOW.md` - **PRZECZYTAJ TO!**
- 📈 Historia uruchomień (50 ostatnich)
- 🎯 Porównanie: manualne vs automatyczne strojenie

**Wklej do pracy:**
- Tabela oszczędności czasu → Rozdział "Wnioski"
- Metryki → Rozdział "Wydajność CI/CD"
- Badge → README.md (już dodany!)

---

### 3️⃣ Automatyczne wdrożenie GitOps (opcjonalne)

**Wdróż najlepsze parametry do Kubernetes:**
```powershell
python src/wdrozenie_gitops.py --gitops-repo ../cl-gitops-regulatory
```

**Co się stanie:**
- ✅ Wybierze najlepsze parametry (min IAE)
- 📦 Utworzy ConfigMapy
- 🔧 Zaktualizuje deployments
- 📝 Commituje do GitOps repo
- 📄 Generuje `wyniki/OSTATNIE_WDROZENIE.md`

**Push do remote (opcjonalnie):**
```powershell
python src/wdrozenie_gitops.py --gitops-repo ../cl-gitops-regulatory --push
```

**Wklej do pracy:**
- Workflow GitOps → Rozdział "Wdrożenie"
- Screenshot ConfigMap → Aneks B
- Metryki wdrożenia → Case study

---

## 🎯 Demo - pełny workflow (POLECANE!)

**Interaktywny workflow z wszystkimi etapami:**
```powershell
python demo_full_workflow.py
```

**Co robi:**
1. Strojenie wszystkich 36 kombinacji
2. Walidacja na 3 modelach
3. Generowanie raportu końcowego
4. (Opcjonalnie) Wdrożenie GitOps
5. Podsumowanie z metrykami

**Czas: ~60-90 minut**

---

## 📊 Co masz teraz dla pracy inżynierskiej?

### Materiały gotowe do włączenia:

✅ **Tabele:**
- Porównanie metod strojenia (IAE, Mp, ts, czas)
- Ranking metod (wielokryterialna ocena)
- Metryki CI/CD (oszczędność czasu)

✅ **Wykresy:**
- Boxplot IAE (rozkład dla metod)
- Pass rate (słupkowy)
- Heatmapa czasu obliczeń
- Scatter IAE vs Mp (trade-off)

✅ **Dane:**
- CSV z wszystkimi wynikami (Excel-ready)
- JSON z parametrami regulatorów
- Markdown z metrykami

✅ **Dokumentacja:**
- `DOKUMENTACJA_V2.1.md` - pełny opis nowych funkcji
- `README_v2.md` - instrukcje użycia
- `WYNIKI_EKSPERYMENTOW.md` - raport CI/CD

---

## 💡 Pro tips

### Tip 1: Otwórz raport w przeglądarce
```powershell
# Znajdź najnowszy raport
$raport = Get-ChildItem wyniki/raport_koncowy_*/raport_koncowy.html | Sort-Object LastWriteTime -Descending | Select-Object -First 1
Start-Process $raport.FullName
```

### Tip 2: Wyeksportuj dane do Excel
```powershell
# CSV jest już gotowy!
$csv = Get-ChildItem wyniki/raport_koncowy_*/raport_koncowy_dane.csv | Sort-Object LastWriteTime -Descending | Select-Object -First 1
Start-Process excel.exe $csv.FullName
```

### Tip 3: Skopiuj wykresy do dokumentacji
```powershell
# Utwórz folder dla pracy
New-Item -ItemType Directory -Force -Path "dokumentacja/wykresy"

# Skopiuj wszystkie wykresy
$najnowszy = Get-ChildItem wyniki/raport_koncowy_* -Directory | Sort-Object LastWriteTime -Descending | Select-Object -First 1
Copy-Item "$najnowszy/*.png" -Destination "dokumentacja/wykresy/"

Write-Host "✅ Wykresy skopiowane do dokumentacja/wykresy/"
```

### Tip 4: Zobacz metryki CI/CD
```powershell
cat wyniki/WYNIKI_EKSPERYMENTOW.md
```

### Tip 5: Sprawdź wdrożenie
```powershell
cat wyniki/OSTATNIE_WDROZENIE.md
```

---

## ❓ FAQ

**Q: Które narzędzie uruchomić najpierw?**  
A: Zacznij od `python demo_full_workflow.py` - to interaktywny przewodnik.

**Q: Muszę uruchomić GitOps?**  
A: Nie, to opcjonalne. Możesz tylko wygenerować raporty.

**Q: Gdzie są wyniki?**  
A: Wszystko w folderze `wyniki/`. Raport główny: `wyniki/raport_koncowy_<timestamp>/raport_koncowy.html`

**Q: Jak długo trwa pełny workflow?**  
A: 60-90 minut dla wszystkich 36 kombinacji. Możesz testować tylko wybrane regulatory.

**Q: Co jeśli nie mam repozytorium GitOps?**  
A: GitOps jest opcjonalny. Raporty i metryki działają bez niego.

**Q: Czy mogę użyć danych w pracy?**  
A: TAK! To właśnie cel tych narzędzi. Wszystkie tabele, wykresy i metryki są gotowe do włączenia w pracę inżynierską.

---

## 🆘 Pomoc

**Problem:** Brak modułu matplotlib/pandas/seaborn  
**Rozwiązanie:**
```powershell
pip install matplotlib pandas seaborn pyyaml
```

**Problem:** Błąd przy GitOps  
**Rozwiązanie:** Sprawdź czy repozytorium istnieje:
```powershell
Test-Path ../cl-gitops-regulatory
```

**Problem:** Brak raportów do analizy  
**Rozwiązanie:** Najpierw uruchom pipeline:
```powershell
python src/uruchom_pipeline.py
```

---

## 📚 Więcej informacji

- `README_v2.md` - pełna dokumentacja
- `DOKUMENTACJA_V2.1.md` - szczegóły implementacji
- `src/raport_koncowy.py` - kod generatora raportów
- `src/wdrozenie_gitops.py` - kod wdrożenia
- `src/metryki_pipeline.py` - kod metryk

---

**Powodzenia z pracą inżynierską! 🎓🚀**
