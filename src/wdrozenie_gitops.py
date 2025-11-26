"""
Automatyczne wdrożenie najlepszych parametrów regulatorów do Kubernetes przez GitOps.

Funkcje:
- Czyta najlepsze parametry z plików JSON (wyniki walidacji)
- Aktualizuje ConfigMapy w repozytorium GitOps (cl-gitops-regulatory)
- Tworzy/aktualizuje pliki deployment.yml z nowymi parametrami
- Commituje zmiany do Git z opisem
- Opcjonalnie: tworzy Pull Request zamiast bezpośredniego push
"""

import json
import yaml
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional


class WdrozenieGitOps:
    def __init__(self, 
                 wyniki_dir: str = "wyniki",
                 gitops_repo: str = "../cl-gitops-regulatory",
                 auto_commit: bool = True,
                 auto_push: bool = False):
        self.wyniki_dir = Path(wyniki_dir)
        self.gitops_repo = Path(gitops_repo)
        self.auto_commit = auto_commit
        self.auto_push = auto_push
        
        # Mapowanie modeli na nazwy aplikacji w GitOps
        self.model_to_app = {
            "zbiornik_1rz": "zbiornik-1rz",
            "dwa_zbiorniki": "dwa-zbiorniki",
            "wahadlo_odwrocone": "wahadlo-odwrocone"
        }
        
    def wczytaj_najlepsze_parametry(self, model: str) -> Optional[Dict]:
        """Wczytuje najlepsze parametry dla danego modelu z plików JSON."""
        print(f"\n Szukanie najlepszych parametrów dla modelu: {model}")
        
        # Szukaj plików walidacji dla tego modelu
        raporty = []
        
        # Szukaj w głównym katalogu i podkatalogach
        for pattern in [f"raport_*_{model}.json", f"*/raport_*_{model}.json"]:
            for plik in self.wyniki_dir.glob(pattern):
                if "rozszerzony" not in plik.name:
                    try:
                        with open(plik, "r", encoding="utf-8") as f:
                            raport = json.load(f)
                        
                        # Sprawdź czy raport przeszedł walidację
                        if raport.get("PASS", False):
                            raporty.append(raport)
                    except Exception as e:
                        print(f"[UWAGA] Błąd przy czytaniu {plik}: {e}")
        
        if not raporty:
            print(f"[X] Brak raportów PASS dla modelu {model}")
            return None
        
        # Wybierz najlepszy na podstawie IAE
        najlepszy = min(raporty, key=lambda r: r.get("metryki", {}).get("IAE", float("inf")))
        
        print(f"[OK] Najlepszy raport dla {model}:")
        print(f"   Regulator: {najlepszy.get('regulator')}")
        print(f"   Metoda: {najlepszy.get('metoda')}")
        print(f"   IAE: {najlepszy.get('metryki', {}).get('IAE', 'N/A'):.2f}")
        print(f"   Mp: {najlepszy.get('metryki', {}).get('przeregulowanie', 'N/A'):.1f}%")
        
        # Wczytaj plik z parametrami
        regulator = najlepszy.get("regulator")
        metoda = najlepszy.get("metoda")
        
        # Szukaj pliku z parametrami
        param_file = self.wyniki_dir / f"parametry_{regulator}_{metoda}.json"
        
        # Jeśli nie ma w głównym katalogu, szukaj w podkatalogach
        if not param_file.exists():
            for pattern in [f"parametry_{regulator}_{metoda}.json", 
                          f"*/parametry_{regulator}_{metoda}.json"]:
                matches = list(self.wyniki_dir.glob(pattern))
                if matches:
                    param_file = matches[0]
                    break
        
        if not param_file.exists():
            print(f"[UWAGA] Nie znaleziono pliku z parametrami: {param_file}")
            # Spróbuj wyciągnąć parametry z raportu
            parametry = najlepszy.get("parametry", {})
            if parametry:
                print("[OK] Użyto parametrów z raportu walidacji")
                return {
                    "regulator": regulator,
                    "metoda": metoda,
                    "parametry": parametry,
                    "metryki": najlepszy.get("metryki", {})
                }
            return None
        
        with open(param_file, "r", encoding="utf-8") as f:
            parametry = json.load(f)
        
        return {
            "regulator": regulator,
            "metoda": metoda,
            "parametry": parametry,
            "metryki": najlepszy.get("metryki", {})
        }
    
    def utworz_configmap(self, app_name: str, parametry: Dict) -> str:
        """Tworzy ConfigMap z parametrami regulatora."""
        # Usuń pola techniczne
        params_clean = {k: v for k, v in parametry.items() 
                       if k not in ["czas_obliczen_s", "metryki"]}
        
        configmap = {
            "apiVersion": "v1",
            "kind": "ConfigMap",
            "metadata": {
                "name": f"{app_name}-config",
                "labels": {
                    "app": f"{app_name}-regulator",
                    "updated": datetime.now().strftime("%Y%m%d-%H%M%S")
                }
            },
            "data": {
                "parametry.json": json.dumps(params_clean, indent=2, ensure_ascii=False)
            }
        }
        
        return yaml.dump(configmap, default_flow_style=False, allow_unicode=True, sort_keys=False)
    
    def aktualizuj_deployment(self, app_name: str, parametry_info: Dict) -> bool:
        """Aktualizuje deployment.yml z referencją do nowej ConfigMap."""
        app_path = self.gitops_repo / "kustomize" / "apps" / app_name / "base"
        
        if not app_path.exists():
            print(f"[X] Nie znaleziono ścieżki aplikacji: {app_path}")
            return False
        
        # 1. Utwórz/zaktualizuj ConfigMap
        configmap_file = app_path / "configmap.yml"
        configmap_yaml = self.utworz_configmap(app_name, parametry_info["parametry"])
        
        with open(configmap_file, "w", encoding="utf-8") as f:
            f.write(configmap_yaml)
        
        print(f"[OK] ConfigMap zapisana: {configmap_file}")
        
        # 2. Zaktualizuj deployment.yml - dodaj volumeMounts dla ConfigMap
        deployment_file = app_path / "deployment.yml"
        
        if not deployment_file.exists():
            print(f"[UWAGA] Brak pliku deployment.yml w {app_path}")
            return False
        
        with open(deployment_file, "r", encoding="utf-8") as f:
            deployment = yaml.safe_load(f)
        
        # Dodaj volume i volumeMount
        if "spec" in deployment and "template" in deployment["spec"]:
            template_spec = deployment["spec"]["template"]["spec"]
            
            # Dodaj volume
            if "volumes" not in template_spec:
                template_spec["volumes"] = []
            
            # Usuń stary volume config jeśli istnieje
            template_spec["volumes"] = [v for v in template_spec["volumes"] 
                                       if v.get("name") != "config"]
            
            # Dodaj nowy volume
            template_spec["volumes"].append({
                "name": "config",
                "configMap": {
                    "name": f"{app_name}-config"
                }
            })
            
            # Dodaj volumeMount do kontenera
            if "containers" in template_spec and len(template_spec["containers"]) > 0:
                container = template_spec["containers"][0]
                
                if "volumeMounts" not in container:
                    container["volumeMounts"] = []
                
                # Usuń stary volumeMount jeśli istnieje
                container["volumeMounts"] = [vm for vm in container["volumeMounts"] 
                                            if vm.get("name") != "config"]
                
                # Dodaj nowy volumeMount
                container["volumeMounts"].append({
                    "name": "config",
                    "mountPath": "/app/config",
                    "readOnly": True
                })
                
                # Dodaj adnotację z informacją o parametrach
                if "metadata" not in deployment["spec"]["template"]:
                    deployment["spec"]["template"]["metadata"] = {}
                if "annotations" not in deployment["spec"]["template"]["metadata"]:
                    deployment["spec"]["template"]["metadata"]["annotations"] = {}
                
                deployment["spec"]["template"]["metadata"]["annotations"].update({
                    "regulator.type": parametry_info["regulator"],
                    "tuning.method": parametry_info["metoda"],
                    "updated.at": datetime.now().isoformat(),
                    "metrics.IAE": str(parametry_info["metryki"].get("IAE", "N/A")),
                    "metrics.Mp": str(parametry_info["metryki"].get("przeregulowanie", "N/A"))
                })
        
        # Zapisz zaktualizowany deployment
        with open(deployment_file, "w", encoding="utf-8") as f:
            yaml.dump(deployment, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
        
        print(f"[OK] Deployment zaktualizowany: {deployment_file}")
        
        # 3. Zaktualizuj kustomization.yml - dodaj configmap.yml do resources
        kustomization_file = app_path / "kustomization.yml"
        
        if kustomization_file.exists():
            with open(kustomization_file, "r", encoding="utf-8") as f:
                kustomization = yaml.safe_load(f)
            
            if "resources" not in kustomization:
                kustomization["resources"] = []
            
            if "configmap.yml" not in kustomization["resources"]:
                kustomization["resources"].append("configmap.yml")
            
            with open(kustomization_file, "w", encoding="utf-8") as f:
                yaml.dump(kustomization, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
            
            print(f"[OK] Kustomization zaktualizowany: {kustomization_file}")
        
        return True
    
    def git_commit(self, model: str, parametry_info: Dict):
        """Tworzy commit w repozytorium GitOps."""
        if not self.auto_commit:
            print("[SKIP] Auto-commit wyłączony, pomijam commit")
            return
        
        app_name = self.model_to_app.get(model)
        if not app_name:
            return
        
        try:
            # Przejdź do katalogu GitOps
            app_path = self.gitops_repo / "kustomize" / "apps" / app_name / "base"
            
            # Git add
            subprocess.run(["git", "add", "."], 
                         cwd=str(app_path), 
                         check=True,
                         capture_output=True)
            
            # Commit message
            commit_msg = (
                f"Update {app_name}: {parametry_info['regulator']} via {parametry_info['metoda']}\n\n"
                f"Metryki:\n"
                f"- IAE: {parametry_info['metryki'].get('IAE', 'N/A'):.2f}\n"
                f"- Mp: {parametry_info['metryki'].get('przeregulowanie', 'N/A'):.1f}%\n"
                f"- ts: {parametry_info['metryki'].get('czas_ustalania', 'N/A'):.2f}s\n\n"
                f"Auto-generated by PID-CD pipeline @ {datetime.now().isoformat()}"
            )
            
            subprocess.run(["git", "commit", "-m", commit_msg],
                         cwd=str(self.gitops_repo),
                         check=True,
                         capture_output=True)
            
            print(f"[OK] Git commit utworzony")
            
            # Push jeśli włączony
            if self.auto_push:
                print("📤 Pushing do remote repository...")
                subprocess.run(["git", "push"],
                             cwd=str(self.gitops_repo),
                             check=True,
                             capture_output=True)
                print("[OK] Zmiany wypchnięte do remote")
            else:
                print("[SKIP] Auto-push wyłączony - użyj 'git push' ręcznie")
                
        except subprocess.CalledProcessError as e:
            print(f"[UWAGA] Błąd Git: {e}")
            print(f"   stdout: {e.stdout.decode('utf-8') if e.stdout else ''}")
            print(f"   stderr: {e.stderr.decode('utf-8') if e.stderr else ''}")
    
    def generuj_podsumowanie(self, wdrozone: Dict[str, Dict]):
        """Generuje plik podsumowujący wdrożenie."""
        output_file = self.wyniki_dir / f"wdrozenie_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(wdrozone, f, indent=2, ensure_ascii=False)
        
        print(f"\n[OK] Podsumowanie wdrożenia zapisane: {output_file}")
        
        # Wygeneruj też markdown dla README
        md_file = self.wyniki_dir / "OSTATNIE_WDROZENIE.md"
        
        md = []
        md.append("# Ostatnie wdrożenie regulatorów\n")
        md.append(f"**Data wdrożenia:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        md.append("## Wdrożone modele\n")
        
        for model, info in wdrozone.items():
            md.append(f"### {model.replace('_', ' ').title()}\n")
            md.append(f"- **Regulator:** `{info['regulator']}`\n")
            md.append(f"- **Metoda strojenia:** `{info['metoda']}`\n")
            md.append(f"- **Parametry:** {json.dumps(info['parametry'], ensure_ascii=False)}\n")
            md.append(f"- **Metryki jakości:**\n")
            md.append(f"  - IAE: `{info['metryki'].get('IAE', 'N/A'):.2f}`\n")
            md.append(f"  - Mp: `{info['metryki'].get('przeregulowanie', 'N/A'):.1f}%`\n")
            md.append(f"  - ts: `{info['metryki'].get('czas_ustalania', 'N/A'):.2f}s`\n")
            md.append(f"- **Status:** [OK] DEPLOYED\n\n")
        
        with open(md_file, "w", encoding="utf-8") as f:
            f.write("".join(md))
        
        print(f"[OK] Markdown wdrożenia zapisany: {md_file}")
    
    def wdroz_wszystkie_modele(self):
        """Wdraża najlepsze regulatory dla wszystkich modeli."""
        print("=" * 70)
        print("[START] AUTOMATYCZNE WDROŻENIE GITOPS")
        print("=" * 70)
        print(f"Repozytorium GitOps: {self.gitops_repo.resolve()}")
        print(f"Auto-commit: {self.auto_commit}")
        print(f"Auto-push: {self.auto_push}\n")
        
        wdrozone = {}
        
        for model, app_name in self.model_to_app.items():
            print(f"\n{'='*70}")
            print(f" Model: {model} → Aplikacja: {app_name}")
            print('='*70)
            
            # 1. Wczytaj najlepsze parametry
            parametry_info = self.wczytaj_najlepsze_parametry(model)
            
            if not parametry_info:
                print(f"[SKIP] Pomijam model {model} - brak danych")
                continue
            
            # 2. Aktualizuj deployment
            success = self.aktualizuj_deployment(app_name, parametry_info)
            
            if not success:
                print(f"[X] Błąd podczas aktualizacji {app_name}")
                continue
            
            # 3. Commit (jeśli włączony)
            self.git_commit(model, parametry_info)
            
            wdrozone[model] = parametry_info
        
        # 4. Podsumowanie
        if wdrozone:
            self.generuj_podsumowanie(wdrozone)
            
            print("\n" + "=" * 70)
            print("[OK] WDROŻENIE ZAKOŃCZONE POMYŚLNIE")
            print("=" * 70)
            print(f"\n[ANALIZA] Wdrożono {len(wdrozone)}/{len(self.model_to_app)} modeli")
            print("\n[SZUKANIE] Następne kroki:")
            
            if self.auto_commit and not self.auto_push:
                print("  1. Sprawdź zmiany: cd", self.gitops_repo.resolve(), "&& git status")
                print("  2. Push do remote: git push")
                print("  3. ArgoCD/FluxCD automatycznie wdroży na klaster")
            elif self.auto_commit and self.auto_push:
                print("  1. ArgoCD/FluxCD automatycznie wdroży na klaster")
                print("  2. Monitoruj status: kubectl get pods -n <namespace>")
            else:
                print("  1. Przejrzyj zmiany w:", self.gitops_repo.resolve())
                print("  2. Zatwierdź i wypchnij ręcznie")
                print("  3. ArgoCD/FluxCD automatycznie wdroży na klaster")
        else:
            print("\n[UWAGA] Brak modeli do wdrożenia")
        
        return wdrozone


def main():
    """Funkcja główna - uruchamianie z linii komend."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Automatyczne wdrożenie regulatorów przez GitOps")
    parser.add_argument("--wyniki-dir", default="wyniki", help="Katalog z wynikami")
    parser.add_argument("--gitops-repo", default="../cl-gitops-regulatory", 
                       help="Ścieżka do repozytorium GitOps")
    parser.add_argument("--no-commit", action="store_true", 
                       help="Wyłącz automatyczny commit")
    parser.add_argument("--push", action="store_true", 
                       help="Włącz automatyczny push do remote")
    parser.add_argument("--model", type=str, default=None,
                       help="Wdróż tylko konkretny model (zbiornik_1rz, dwa_zbiorniki, wahadlo_odwrocone)")
    
    args = parser.parse_args()
    
    wdrozenie = WdrozenieGitOps(
        wyniki_dir=args.wyniki_dir,
        gitops_repo=args.gitops_repo,
        auto_commit=not args.no_commit,
        auto_push=args.push
    )
    
    if args.model:
        # Wdróż tylko konkretny model
        parametry_info = wdrozenie.wczytaj_najlepsze_parametry(args.model)
        if parametry_info:
            app_name = wdrozenie.model_to_app.get(args.model)
            if app_name:
                wdrozenie.aktualizuj_deployment(app_name, parametry_info)
                wdrozenie.git_commit(args.model, parametry_info)
    else:
        # Wdróż wszystkie modele
        wdrozenie.wdroz_wszystkie_modele()


if __name__ == "__main__":
    main()
