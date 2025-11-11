"""Test modułu metryk pipeline."""
from src.metryki_pipeline import MetrykiPipeline
import time

print("\n" + "="*60)
print("[CZAS] TEST MODUŁU METRYK PIPELINE")
print("="*60 + "\n")

# Inicjalizacja
m = MetrykiPipeline('wyniki')

# Symulacja pipeline
print("[START] Symulacja etapów pipeline...\n")

with m.zmierz_etap('Test strojenia'):
    time.sleep(1)

with m.zmierz_etap('Test walidacji'):
    time.sleep(0.5)

with m.zmierz_etap('Test raportowania'):
    time.sleep(0.3)

# Zakończ i zapisz
m.zakoncz_run('success')

# Generuj raporty
print("\n[ANALIZA] Generowanie raportów...")
m.generuj_badge_svg()
m.generuj_raport_markdown()

print("\n[OK] Test zakończony pomyślnie!")
print("\nWygenerowane pliki:")
print("  - wyniki/pipeline_badge.svg")
print("  - wyniki/WYNIKI_EKSPERYMENTOW.md")
print("  - wyniki/pipeline_metrics.json")
print("  - wyniki/pipeline_history.json")
