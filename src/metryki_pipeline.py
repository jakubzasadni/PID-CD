"""
Moduł do pomiaru i zapisywania metryk CI/CD pipeline.
Śledzi czas wykonania każdego etapu, zapisuje historię, generuje raporty.
"""

import json
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from contextlib import contextmanager


class MetrykiPipeline:
    def __init__(self, wyniki_dir: str = "wyniki"):
        self.wyniki_dir = Path(wyniki_dir)
        self.wyniki_dir.mkdir(exist_ok=True)
        
        self.metryki_file = self.wyniki_dir / "pipeline_metrics.json"
        self.historia_file = self.wyniki_dir / "pipeline_history.json"
        
        self.current_run = {
            "start_time": datetime.now().isoformat(),
            "etapy": {},
            "status": "running"
        }
        
    @contextmanager
    def zmierz_etap(self, nazwa_etapu: str):
        """Context manager do pomiaru czasu etapu pipeline."""
        print(f"\n[CZAS] START: {nazwa_etapu}")
        start = time.time()
        
        try:
            yield
            czas = time.time() - start
            self.current_run["etapy"][nazwa_etapu] = {
                "czas_s": round(czas, 2),
                "status": "success",
                "koniec": datetime.now().isoformat()
            }
            print(f"[OK] KONIEC: {nazwa_etapu} ({czas:.2f}s)")
            
        except Exception as e:
            czas = time.time() - start
            self.current_run["etapy"][nazwa_etapu] = {
                "czas_s": round(czas, 2),
                "status": "failed",
                "error": str(e),
                "koniec": datetime.now().isoformat()
            }
            print(f"[X] BŁĄD: {nazwa_etapu} ({czas:.2f}s) - {e}")
            raise
    
    def zakoncz_run(self, status: str = "success"):
        """Kończy pomiar i zapisuje metryki."""
        self.current_run["end_time"] = datetime.now().isoformat()
        self.current_run["status"] = status
        
        # Oblicz całkowity czas
        start = datetime.fromisoformat(self.current_run["start_time"])
        end = datetime.fromisoformat(self.current_run["end_time"])
        total_time = (end - start).total_seconds()
        self.current_run["total_time_s"] = round(total_time, 2)
        
        # Zapisz aktualne metryki
        with open(self.metryki_file, "w", encoding="utf-8") as f:
            json.dump(self.current_run, f, indent=2, ensure_ascii=False)
        
        # Dodaj do historii
        self._dodaj_do_historii()
        
        print(f"\n{'='*70}")
        print(f"[ANALIZA] METRYKI PIPELINE")
        print(f"{'='*70}")
        print(f"Status: {status.upper()}")
        print(f"Całkowity czas: {total_time:.2f}s ({timedelta(seconds=int(total_time))})")
        print(f"\nCzasy etapów:")
        for etap, dane in self.current_run["etapy"].items():
            status_emoji = "[OK]" if dane["status"] == "success" else "[X]"
            print(f"  {status_emoji} {etap}: {dane['czas_s']}s")
        print(f"{'='*70}\n")
    
    def _dodaj_do_historii(self):
        """Dodaje aktualny run do historii."""
        historia = []
        
        if self.historia_file.exists():
            with open(self.historia_file, "r", encoding="utf-8") as f:
                historia = json.load(f)
        
        historia.append(self.current_run)
        
        # Zachowaj tylko ostatnie 50 runów
        historia = historia[-50:]
        
        with open(self.historia_file, "w", encoding="utf-8") as f:
            json.dump(historia, f, indent=2, ensure_ascii=False)
    
    def pobierz_statystyki(self) -> Dict:
        """Pobiera statystyki z historii pipeline."""
        if not self.historia_file.exists():
            return {}
        
        with open(self.historia_file, "r", encoding="utf-8") as f:
            historia = json.load(f)
        
        if not historia:
            return {}
        
        # Statystyki
        success_runs = [r for r in historia if r["status"] == "success"]
        failed_runs = [r for r in historia if r["status"] == "failed"]
        
        czasy = [r["total_time_s"] for r in success_runs if "total_time_s" in r]
        
        stats = {
            "total_runs": len(historia),
            "success_runs": len(success_runs),
            "failed_runs": len(failed_runs),
            "success_rate": round(len(success_runs) / len(historia) * 100, 1) if historia else 0,
            "avg_time_s": round(sum(czasy) / len(czasy), 2) if czasy else 0,
            "min_time_s": round(min(czasy), 2) if czasy else 0,
            "max_time_s": round(max(czasy), 2) if czasy else 0,
            "last_run": historia[-1]
        }
        
        return stats
    
    def generuj_badge_svg(self, output_file: str = None):
        """Generuje badge SVG z czasem ostatniego pipeline."""
        if output_file is None:
            output_file = self.wyniki_dir / "pipeline_badge.svg"
        
        stats = self.pobierz_statystyki()
        
        if not stats:
            time_str = "N/A"
            color = "lightgrey"
        else:
            last_time = stats["last_run"].get("total_time_s", 0)
            time_str = f"{timedelta(seconds=int(last_time))}"
            
            # Kolor zależny od statusu
            if stats["last_run"]["status"] == "success":
                color = "brightgreen"
            else:
                color = "red"
        
        # Prosty SVG badge
        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="180" height="20">
  <linearGradient id="b" x2="0" y2="100%">
    <stop offset="0" stop-color="#bbb" stop-opacity=".1"/>
    <stop offset="1" stop-opacity=".1"/>
  </linearGradient>
  <mask id="a">
    <rect width="180" height="20" rx="3" fill="#fff"/>
  </mask>
  <g mask="url(#a)">
    <path fill="#555" d="M0 0h90v20H0z"/>
    <path fill="{color}" d="M90 0h90v20H90z"/>
    <path fill="url(#b)" d="M0 0h180v20H0z"/>
  </g>
  <g fill="#fff" text-anchor="middle" font-family="DejaVu Sans,Verdana,Geneva,sans-serif" font-size="11">
    <text x="45" y="15" fill="#010101" fill-opacity=".3">pipeline time</text>
    <text x="45" y="14">pipeline time</text>
    <text x="135" y="15" fill="#010101" fill-opacity=".3">{time_str}</text>
    <text x="135" y="14">{time_str}</text>
  </g>
</svg>'''
        
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(svg)
        
        print(f"[OK] Badge zapisany: {output_file}")
        return output_file
    
    def generuj_raport_markdown(self, output_file: str = None):
        """Generuje raport markdown z metrykami."""
        if output_file is None:
            output_file = self.wyniki_dir / "WYNIKI_EKSPERYMENTOW.md"
        
        stats = self.pobierz_statystyki()
        
        if not stats:
            print("[UWAGA] Brak danych do wygenerowania raportu")
            return
        
        md = []
        md.append("# Wyniki eksperymentów CI/CD\n")
        md.append(f"**Ostatnia aktualizacja:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        # Badge
        md.append("![Pipeline Time](pipeline_badge.svg)\n")
        
        # Statystyki ogólne
        md.append("## Statystyki pipeline\n")
        md.append(f"- **Całkowita liczba uruchomień:** {stats['total_runs']}\n")
        md.append(f"- **Udane uruchomienia:** {stats['success_runs']} ({stats['success_rate']:.1f}%)\n")
        md.append(f"- **Nieudane uruchomienia:** {stats['failed_runs']}\n")
        md.append(f"- **Średni czas wykonania:** {timedelta(seconds=int(stats['avg_time_s']))}\n")
        md.append(f"- **Najszybszy run:** {timedelta(seconds=int(stats['min_time_s']))}\n")
        md.append(f"- **Najwolniejszy run:** {timedelta(seconds=int(stats['max_time_s']))}\n\n")
        
        # Ostatni run
        last_run = stats["last_run"]
        status_emoji = "[OK]" if last_run["status"] == "success" else "[X]"
        
        md.append("## Ostatnie uruchomienie\n")
        md.append(f"- **Status:** {status_emoji} {last_run['status'].upper()}\n")
        md.append(f"- **Data:** {last_run['start_time']}\n")
        md.append(f"- **Czas trwania:** {timedelta(seconds=int(last_run.get('total_time_s', 0)))}\n\n")
        
        md.append("### Czasy etapów\n")
        md.append("| Etap | Czas | Status |\n")
        md.append("|------|------|--------|\n")
        
        for etap, dane in last_run.get("etapy", {}).items():
            status_emoji = "[OK]" if dane["status"] == "success" else "[X]"
            md.append(f"| {etap} | {dane['czas_s']}s | {status_emoji} {dane['status']} |\n")
        
        md.append("\n")
        
        # Porównanie z manualnym strojeniem
        md.append("## Porównanie: Automatyczne vs Manualne strojenie\n")
        md.append("| Aspekt | Manualne strojenie | CI/CD Pipeline | Oszczędność |\n")
        md.append("|--------|-------------------|----------------|-------------|\n")
        
        manual_time = 4 * 3 * 3 * 30  # 4 regulatory × 3 modele × 3 metody × 30 min
        auto_time = stats.get('avg_time_s', 0) / 60
        savings = manual_time - auto_time
        savings_percent = (savings / manual_time * 100) if manual_time > 0 else 0
        
        md.append(f"| Czas (godz) | ~{manual_time/60:.1f}h | ~{auto_time/60:.1f}h | {savings/60:.1f}h ({savings_percent:.0f}%) |\n")
        md.append(f"| Powtarzalność | Niska | Wysoka | [OK] |\n")
        md.append(f"| Błądy ludzkie | Możliwe | Wyeliminowane | [OK] |\n")
        md.append(f"| Dokumentacja | Manualna | Automatyczna | [OK] |\n")
        md.append(f"| Wdrożenie | Manualne | Automatyczne (GitOps) | [OK] |\n\n")
        
        # Historia ostatnich 10 runów
        if self.historia_file.exists():
            with open(self.historia_file, "r", encoding="utf-8") as f:
                historia = json.load(f)
            
            md.append("## Historia ostatnich 10 uruchomień\n")
            md.append("| # | Data | Status | Czas | Etapy OK |\n")
            md.append("|---|------|--------|------|----------|\n")
            
            for i, run in enumerate(reversed(historia[-10:]), 1):
                status_emoji = "[OK]" if run["status"] == "success" else "[X]"
                total_time = run.get("total_time_s", 0)
                etapy_ok = sum(1 for e in run.get("etapy", {}).values() if e["status"] == "success")
                etapy_total = len(run.get("etapy", {}))
                data = run["start_time"][:10]  # YYYY-MM-DD
                
                md.append(f"| {i} | {data} | {status_emoji} | {total_time:.0f}s | {etapy_ok}/{etapy_total} |\n")
        
        md.append("\n---\n")
        md.append("*Raport generowany automatycznie przez `src/metryki_pipeline.py`*\n")
        
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("".join(md))
        
        print(f"[OK] Raport markdown zapisany: {output_file}")
        return output_file


def main():
    """Testowanie modułu."""
    metryki = MetrykiPipeline()
    
    # Symulacja pipeline
    try:
        with metryki.zmierz_etap("Strojenie"):
            time.sleep(2)
        
        with metryki.zmierz_etap("Walidacja"):
            time.sleep(1.5)
        
        with metryki.zmierz_etap("Generowanie raportów"):
            time.sleep(0.5)
        
        metryki.zakoncz_run("success")
        
    except Exception as e:
        metryki.zakoncz_run("failed")
        raise
    
    # Generuj raporty
    metryki.generuj_badge_svg()
    metryki.generuj_raport_markdown()
    
    # Wyświetl statystyki
    stats = metryki.pobierz_statystyki()
    print(f"\n[ANALIZA] Statystyki: {json.dumps(stats, indent=2, ensure_ascii=False)}")


if __name__ == "__main__":
    main()
