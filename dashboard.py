"""
Prosty dashboard tekstowy pokazujący podsumowanie wyników projektu.
"""

from pathlib import Path
import json
from datetime import datetime

def wyswietl_dashboard():
    """Wyświetla dashboard z podsumowaniem projektu."""
    
    print("\n" + "="*80)
    print(" "*25 + " DASHBOARD PROJEKTU INŻYNIERSKIEGO")
    print("="*80)
    print(f"\n📅 Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # 1. Statystyki raportów walidacji
    print("━"*80)
    print("[ANALIZA] STATYSTYKI WALIDACJI")
    print("━"*80)
    
    wyniki_dir = Path("wyniki")
    raporty = list(wyniki_dir.glob("raport_*.json"))
    raporty = [r for r in raporty if "rozszerzony" not in r.name]
    
    if raporty:
        pass_count = 0
        fail_count = 0
        regulatory_stats = {}
        
        for raport_file in raporty:
            try:
                with open(raport_file, 'r', encoding='utf-8') as f:
                    raport = json.load(f)
                
                regulator = raport.get("regulator", "unknown")
                passed = raport.get("PASS", False)
                
                if passed:
                    pass_count += 1
                else:
                    fail_count += 1
                
                if regulator not in regulatory_stats:
                    regulatory_stats[regulator] = {"pass": 0, "fail": 0}
                
                if passed:
                    regulatory_stats[regulator]["pass"] += 1
                else:
                    regulatory_stats[regulator]["fail"] += 1
                    
            except Exception:
                continue
        
        total = pass_count + fail_count
        pass_rate = (pass_count / total * 100) if total > 0 else 0
        
        print(f"  Całkowita liczba testów: {total}")
        print(f"  [OK] Przeszło: {pass_count} ({pass_rate:.1f}%)")
        print(f"  [X] Nie przeszło: {fail_count}")
        print()
        
        # Statystyki per regulator
        print("  Statystyki regulatorów:")
        for reg, stats in sorted(regulatory_stats.items()):
            total_reg = stats["pass"] + stats["fail"]
            pass_rate_reg = (stats["pass"] / total_reg * 100) if total_reg > 0 else 0
            print(f"    • {reg:20} → {stats['pass']}/{total_reg} ({pass_rate_reg:.0f}%)")
    else:
        print("  [UWAGA] Brak raportów walidacji")
    
    # 2. Najnowszy raport końcowy
    print("\n" + "━"*80)
    print("[WYKRESY] OSTATNI RAPORT KOŃCOWY")
    print("━"*80)
    
    raporty_koncowe = sorted(wyniki_dir.glob("raport_koncowy_*/raport_koncowy.html"))
    if raporty_koncowe:
        najnowszy = raporty_koncowe[-1]
        timestamp = najnowszy.parent.name.replace("raport_koncowy_", "")
        
        print(f"  Data wygenerowania: {timestamp[:8]} {timestamp[9:11]}:{timestamp[11:13]}")
        print(f"  Lokalizacja: {najnowszy.parent}")
        print(f"  Pliki:")
        
        for file in sorted(najnowszy.parent.iterdir()):
            size_kb = file.stat().st_size / 1024
            if file.suffix == ".html":
                print(f"    📄 {file.name:35} ({size_kb:.1f} KB) ⭐ OTWÓRZ W PRZEGLĄDARCE")
            elif file.suffix == ".csv":
                print(f"    [ANALIZA] {file.name:35} ({size_kb:.1f} KB)")
            elif file.suffix == ".png":
                print(f"    🖼️ {file.name:35} ({size_kb:.1f} KB)")
    else:
        print("  [UWAGA] Brak raportu końcowego - uruchom: python src/raport_koncowy.py")
    
    # 3. Metryki CI/CD
    print("\n" + "━"*80)
    print("[CZAS] METRYKI CI/CD PIPELINE")
    print("━"*80)
    
    metryki_file = wyniki_dir / "pipeline_metrics.json"
    if metryki_file.exists():
        with open(metryki_file, 'r', encoding='utf-8') as f:
            metryki = json.load(f)
        
        total_time = metryki.get("total_time_s", 0)
        status = metryki.get("status", "unknown")
        status_emoji = "[OK]" if status == "success" else "[X]"
        
        print(f"  Status ostatniego run: {status_emoji} {status.upper()}")
        print(f"  Całkowity czas: {total_time:.1f}s (~{total_time/60:.1f} min)")
        print(f"  Etapy:")
        
        for etap, dane in metryki.get("etapy", {}).items():
            status_e = "[OK]" if dane["status"] == "success" else "[X]"
            print(f"    {status_e} {etap:30} → {dane['czas_s']:.2f}s")
        
        # Historia
        historia_file = wyniki_dir / "pipeline_history.json"
        if historia_file.exists():
            with open(historia_file, 'r', encoding='utf-8') as f:
                historia = json.load(f)
            
            success_runs = sum(1 for r in historia if r.get("status") == "success")
            total_runs = len(historia)
            success_rate = (success_runs / total_runs * 100) if total_runs > 0 else 0
            
            print(f"\n  Historia ({len(historia)} uruchomień):")
            print(f"    Success rate: {success_rate:.1f}% ({success_runs}/{total_runs})")
    else:
        print("  [UWAGA] Brak metryk - uruchom pipeline z pomiarem czasu")
    
    # 4. Ostatnie wdrożenie
    print("\n" + "━"*80)
    print("[START] OSTATNIE WDROŻENIE GITOPS")
    print("━"*80)
    
    wdrozenie_file = wyniki_dir / "OSTATNIE_WDROZENIE.md"
    if wdrozenie_file.exists():
        # Czytaj datę z pliku
        with open(wdrozenie_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Znajdź datę
        for line in lines:
            if "Data wdrożenia:" in line:
                data = line.split("**Data wdrożenia:**")[1].strip()
                print(f"  Data wdrożenia: {data}")
                break
        
        # Policz wdrożone modele
        deployed_count = sum(1 for line in lines if "[OK] DEPLOYED" in line)
        print(f"  Wdrożone modele: {deployed_count}/3")
        print(f"  Szczegóły: wyniki/OSTATNIE_WDROZENIE.md")
    else:
        print("  [UWAGA] Brak wdrożenia - uruchom: python src/wdrozenie_gitops.py")
    
    # 5. Quick actions
    print("\n" + "━"*80)
    print(" SZYBKIE AKCJE")
    print("━"*80)
    print("""
  1. Wygeneruj raport końcowy:
     python src/raport_koncowy.py

  2. Otwórz ostatni raport w przeglądarce:
     Start-Process (Get-ChildItem wyniki/raport_koncowy_*/raport_koncowy.html | Sort LastWriteTime -Desc | Select -First 1).FullName

  3. Zobacz metryki CI/CD:
     Get-Content wyniki/WYNIKI_EKSPERYMENTOW.md

  4. Wdróż do Kubernetes:
     python src/wdrozenie_gitops.py --gitops-repo ../cl-gitops-regulatory

  5. Uruchom demo workflow:
     python demo_full_workflow.py
""")
    
    print("="*80)
    print(" "*20 + " Powodzenia z pracą inżynierską! [START]")
    print("="*80 + "\n")


if __name__ == "__main__":
    try:
        wyswietl_dashboard()
    except Exception as e:
        print(f"\n[X] Błąd: {e}")
        import traceback
        traceback.print_exc()
