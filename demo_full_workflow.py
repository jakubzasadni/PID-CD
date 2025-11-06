"""
DEMO: Pełny workflow CI/CD dla projektu inżynierskiego

Ten skrypt pokazuje kompletny workflow:
1. Strojenie wszystkich regulatorów na wszystkich modelach
2. Walidacja wyników
3. Generowanie raportu końcowego porównawczego
4. Automatyczne wdrożenie najlepszych parametrów do Kubernetes (GitOps)

Użycie:
    python demo_full_workflow.py
"""

import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime

def print_header(text):
    """Drukuje nagłówek sekcji."""
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70 + "\n")

def run_command(cmd, description, cwd=None):
    """Uruchamia komendę i wyświetla wynik."""
    print(f"🚀 {description}")
    print(f"   Komenda: {cmd}")
    
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True
        )
        print(f"✅ Sukces!")
        if result.stdout:
            print(f"   Output: {result.stdout[:200]}")  # Pierwsze 200 znaków
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Błąd: {e}")
        if e.stderr:
            print(f"   Error: {e.stderr[:200]}")
        return False

def main():
    print_header("🎓 DEMO: Pełny workflow CI/CD - Projekt Inżynierski")
    print("Automatyzacja procesu strojenia, walidacji i wdrożeń")
    print("aplikacji sterowania procesami w środowisku Kubernetes\n")
    
    start_time = datetime.now()
    
    # Lista modeli i regulatorów
    modele = ["zbiornik_1rz", "dwa_zbiorniki", "wahadlo_odwrocone"]
    regulatory = ["regulator_p", "regulator_pi", "regulator_pd", "regulator_pid"]
    
    print(f"📋 Konfiguracja:")
    print(f"   Modele: {', '.join(modele)}")
    print(f"   Regulatory: {', '.join(regulatory)}")
    print(f"   Metody: Ziegler-Nichols, Siatka, Optymalizacja")
    print(f"   Łącznie kombinacji: {len(modele) * len(regulatory) * 3} = 36")
    
    input("\n▶️ Naciśnij Enter aby rozpocząć pełny workflow...")
    
    # =========================================================================
    # ETAP 1: Strojenie i walidacja wszystkich kombinacji
    # =========================================================================
    print_header("ETAP 1/4: Strojenie i walidacja wszystkich regulatorów")
    
    for regulator in regulatory:
        for model in modele:
            print(f"\n📊 {regulator} + {model}")
            
            # Strojenie
            os.environ["REGULATOR"] = regulator
            os.environ["MODEL"] = model
            os.environ["TRYB"] = "strojenie"
            
            cmd = f"python src/uruchom_symulacje.py"
            run_command(cmd, f"Strojenie {regulator} na {model}")
            
            # Walidacja
            os.environ["TRYB"] = "walidacja"
            run_command(cmd, f"Walidacja {regulator} na {model}")
    
    # =========================================================================
    # ETAP 2: Generowanie raportu końcowego
    # =========================================================================
    print_header("ETAP 2/4: Generowanie raportu końcowego porównawczego")
    
    cmd = "python src/raport_koncowy.py --wyniki-dir wyniki"
    success = run_command(cmd, "Generowanie raportu końcowego")
    
    if success:
        print("\n📄 Raport końcowy wygenerowany!")
        print("   Sprawdź: wyniki/raport_koncowy_<timestamp>/raport_koncowy.html")
    
    # =========================================================================
    # ETAP 3: Automatyczne wdrożenie GitOps
    # =========================================================================
    print_header("ETAP 3/4: Automatyczne wdrożenie do Kubernetes (GitOps)")
    
    gitops_repo = Path("../cl-gitops-regulatory")
    
    if gitops_repo.exists():
        print(f"✅ Repozytorium GitOps znalezione: {gitops_repo.resolve()}")
        
        deploy_choice = input("\n🚀 Czy wdrożyć najlepsze parametry do Kubernetes? (t/N): ")
        
        if deploy_choice.lower() in ['t', 'y', 'tak', 'yes']:
            cmd = f"python src/wdrozenie_gitops.py --gitops-repo {gitops_repo}"
            
            # Zapytaj o auto-push
            push_choice = input("   Push do remote repository? (t/N): ")
            if push_choice.lower() in ['t', 'y', 'tak', 'yes']:
                cmd += " --push"
            
            success = run_command(cmd, "Wdrożenie przez GitOps")
            
            if success:
                print("\n✅ Parametry wdrożone!")
                print("   Sprawdź: wyniki/OSTATNIE_WDROZENIE.md")
                print("   GitOps: ArgoCD/FluxCD automatycznie zsynchronizuje klaster")
        else:
            print("⏭️ Pomijam wdrożenie (można uruchomić później)")
    else:
        print(f"⚠️ Repozytorium GitOps nie znalezione: {gitops_repo}")
        print("   Pomijam etap wdrożenia")
    
    # =========================================================================
    # ETAP 4: Podsumowanie i metryki
    # =========================================================================
    print_header("ETAP 4/4: Podsumowanie i metryki CI/CD")
    
    end_time = datetime.now()
    total_time = (end_time - start_time).total_seconds()
    
    print(f"⏱️  Całkowity czas workflow: {total_time:.1f}s ({total_time/60:.1f} min)")
    print(f"📊 Liczba przetestowanych kombinacji: 36")
    print(f"⚡ Średni czas na kombinację: {total_time/36:.1f}s")
    
    # Wyświetl metryki pipeline
    if Path("wyniki/WYNIKI_EKSPERYMENTOW.md").exists():
        print("\n📈 Raport metryk CI/CD:")
        with open("wyniki/WYNIKI_EKSPERYMENTOW.md", "r", encoding="utf-8") as f:
            lines = f.readlines()[:20]  # Pierwsze 20 linii
            print("".join(lines))
    
    # =========================================================================
    # WNIOSKI I NASTĘPNE KROKI
    # =========================================================================
    print_header("✅ WORKFLOW ZAKOŃCZONY")
    
    print("📂 Wygenerowane pliki:\n")
    print("1. Wyniki strojenia:")
    print("   - wyniki/parametry_*.json - parametry regulatorów")
    print("   - wyniki/raport_strojenie_*.html - raporty HTML dla każdej metody")
    print("")
    print("2. Wyniki walidacji:")
    print("   - wyniki/raport_*.json - raporty walidacji")
    print("   - wyniki/wykres_*.png - wykresy odpowiedzi układu")
    print("")
    print("3. Raport końcowy:")
    print("   - wyniki/raport_koncowy_<timestamp>/raport_koncowy.html")
    print("   - wyniki/raport_koncowy_<timestamp>/raport_koncowy_dane.csv")
    print("   - wyniki/raport_koncowy_<timestamp>/porownanie_*.png")
    print("")
    print("4. Metryki CI/CD:")
    print("   - wyniki/WYNIKI_EKSPERYMENTOW.md - raport porównawczy")
    print("   - wyniki/pipeline_badge.svg - badge czasu pipeline")
    print("   - wyniki/pipeline_metrics.json - metryki ostatniego run")
    print("")
    print("5. Wdrożenie GitOps:")
    print("   - wyniki/OSTATNIE_WDROZENIE.md - info o wdrożonych parametrach")
    print("   - ../cl-gitops-regulatory/kustomize/apps/*/base/configmap.yml")
    print("")
    
    print("\n🎯 Następne kroki:")
    print("1. Przejrzyj raport końcowy w przeglądarce")
    print("2. Sprawdź WYNIKI_EKSPERYMENTOW.md dla metryk CI/CD")
    print("3. Jeśli wdrożono do GitOps:")
    print("   - Sprawdź status w ArgoCD/FluxCD")
    print("   - Monitoruj wdrożenie: kubectl get pods")
    print("4. Użyj danych CSV do dalszej analizy (Excel, Python, R)")
    
    print("\n" + "=" * 70)
    print("🎓 Praca inżynierska: Dane gotowe do dokumentacji!")
    print("=" * 70)
    
    # Opcjonalnie otwórz raport w przeglądarce
    open_choice = input("\n🌐 Otworzyć raport końcowy w przeglądarce? (t/N): ")
    if open_choice.lower() in ['t', 'y', 'tak', 'yes']:
        raport_dir = Path("wyniki")
        latest_raport = sorted(raport_dir.glob("raport_koncowy_*/raport_koncowy.html"))
        if latest_raport:
            raport_file = latest_raport[-1]
            import webbrowser
            webbrowser.open(raport_file.as_uri())
            print(f"✅ Otwarto: {raport_file}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ Workflow przerwany przez użytkownika")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Błąd: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
