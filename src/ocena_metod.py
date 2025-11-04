"""
Analiza i porównanie wyników walidacji regulatorów.
Tworzy raport HTML z kolorowym oznaczeniem PASS/FAIL,
procentem zaliczonych modeli oraz listę modeli do wdrożenia.
Porównuje regulatory (PID, PI, P, PD) między sobą.
"""

import os
import json
from pathlib import Path
from statistics import mean


def _dash(x):
    return "-" if x is None else x


def ocena_metod(wyniki_dir: str):
    wyniki_path = Path(wyniki_dir)

    # --- Raporty z walidacji (tylko standardowe, bez rozszerzonych) ---
    raporty = sorted([f for f in wyniki_path.glob("raport_*.json") if "rozszerzony" not in f.name])
    if not raporty:
        print("⚠️ Brak raportów do oceny w katalogu:", wyniki_path)
        return

    dane = []
    regulatory = set()
    for plik in raporty:
        with open(plik, "r") as f:
            r = json.load(f)
        regulatory.add(r["regulator"])
        dane.append(r)

    regulatory = sorted(list(regulatory))

    # --- Agregaty regulatorów ---
    statystyki = {}
    for reg in regulatory:
        wyniki_r = [r for r in dane if r["regulator"] == reg]
        passy = [r for r in wyniki_r if r.get("PASS", False)]
        proc_pass = 100 * len(passy) / len(wyniki_r) if wyniki_r else 0.0
        avg_iae = mean([r["metryki"]["IAE"] for r in wyniki_r]) if wyniki_r else float("inf")
        avg_ts  = mean([r["metryki"]["czas_ustalania"] for r in wyniki_r]) if wyniki_r else float("inf")
        avg_mp  = mean([r["metryki"]["przeregulowanie"] for r in wyniki_r]) if wyniki_r else float("inf")
        statystyki[reg] = {"pass_percent": proc_pass, "avg_IAE": avg_iae, "avg_ts": avg_ts, "avg_Mp": avg_mp}

    najlepszy_regulator = min(statystyki.keys(), key=lambda r: statystyki[r]["avg_IAE"])

    # --- Lista modeli do wdrożenia (PASS) ---
    passed_models = sorted(set([r["model"] for r in dane if r.get("PASS", False)]))
    if passed_models:
        with open(wyniki_path / "passed_models.txt", "w") as f:
            for m in passed_models:
                f.write(m + "\n")
        print("✅ Utworzono listę modeli do wdrożenia:", wyniki_path / "passed_models.txt")
        print("Modele:", ", ".join(passed_models))
    else:
        print("❌ Żaden model nie spełnił progów jakości — brak passed_models.txt")

    # --- HTML ---
    html = []
    html.append("<html><head><meta charset='UTF-8'>")
    html.append("""
    <style>
      body { font-family: Arial, sans-serif; margin: 40px; }
      h1 { color: #2b547e; }
      h2 { margin-top: 36px; }
      table { border-collapse: collapse; width: 100%; margin-top: 14px; }
      th, td { border: 1px solid #ddd; padding: 8px; text-align: center; }
      th { background-color: #f2f2f2; }
      .pass { background-color: #c7f7c7; }
      .fail { background-color: #f9c0c0; }
    </style>
    """)
    html.append("</head><body>")

    html.append("<h1>Raport walidacji regulatorów</h1>")

    # Szczegółowe wyniki
    html.append("<h2>Wyniki walidacji</h2>")
    html.append("<table><tr><th>Regulator</th><th>Metoda strojenia</th><th>Model</th>"
                "<th>IAE</th><th>ISE</th><th>Mp [%]</th><th>ts [s]</th><th>Status</th></tr>")
    for r in dane:
        passed = r.get("PASS", False)
        cls = "pass" if passed else "fail"
        m = r["metryki"]
        html.append(
            f"<tr class='{cls}'><td>{r['regulator']}</td><td>{r['metoda']}</td><td>{r['model']}</td>"
            f"<td>{m['IAE']:.2f}</td><td>{m['ISE']:.2f}</td>"
            f"<td>{m['przeregulowanie']:.1f}</td><td>{m['czas_ustalania']:.1f}</td>"
            f"<td>{'✅ PASS' if passed else '❌ FAIL'}</td></tr>"
        )
    html.append("</table>")

    # Podsumowanie regulatorów
    html.append("<h2>Podsumowanie regulatorów</h2>")
    html.append("<table><tr><th>Regulator</th><th>% PASS</th><th>Średni IAE</th><th>Średni ts [s]</th><th>Średni Mp [%]</th></tr>")
    for reg, s in statystyki.items():
        html.append(f"<tr><td>{reg}</td><td>{s['pass_percent']:.1f}%</td>"
                    f"<td>{s['avg_IAE']:.2f}</td><td>{s['avg_ts']:.2f}</td><td>{s['avg_Mp']:.1f}</td></tr>")
    html.append("</table>")
    html.append(f"<p><b>Najlepszy regulator (wg średniego IAE):</b> <span style='color:green'>{najlepszy_regulator.upper()}</span></p>")

    # Parametry strojenia — skanujemy ZAWSZE wszystkie parametry_*.json
    html.append("<h2>Parametry strojenia</h2>")
    html.append("<table><tr><th>Regulator</th><th>Metoda strojenia</th><th>Kp</th><th>Ti</th><th>Td</th></tr>")
    param_files = sorted(wyniki_path.glob("parametry_*.json"))
    for pf in param_files:
        with open(pf, "r") as f:
            blob = json.load(f)
        reg = blob.get("regulator", "")
        met = blob.get("metoda", "")
        p = blob.get("parametry", {})
        html.append(
            f"<tr><td>{reg}</td><td>{met}</td>"
            f"<td>{_dash(p.get('Kp'))}</td><td>{_dash(p.get('Ti'))}</td><td>{_dash(p.get('Td'))}</td></tr>"
        )
    html.append("</table>")

    raport_html = wyniki_path / "raport.html"
    raport_html.write_text("\n".join(html), encoding="utf-8")

    # JSON z wyborem najlepszego
    with open(wyniki_path / "najlepszy_regulator.json", "w") as f:
        json.dump({"najlepszy_regulator": najlepszy_regulator, "statystyki": statystyki}, f, indent=2)

    print(f"✅ Raport HTML zapisano jako: {raport_html}")
    print(f"✅ Najlepszy regulator: {najlepszy_regulator.upper()} (średni IAE={statystyki[najlepszy_regulator]['avg_IAE']:.2f})")


if __name__ == "__main__":
    ocena_metod("wyniki")
