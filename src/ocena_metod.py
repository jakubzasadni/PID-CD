"""
Analiza i porównanie wyników walidacji regulatorów.
Tworzy raport HTML z kolorowym oznaczeniem PASS/FAIL,
procentem zaliczonych modeli oraz listę modeli do wdrożenia.
Porównuje regulatory (P, PI, PD, PID) między sobą.
"""

import os
import json
from pathlib import Path
from statistics import mean

def _fmt(v):
    """Bezpieczne formatowanie wartości liczbowych i pustych."""
    if v is None or v == "" or v == "-":
        return "-"
    try:
        return f"{float(v):.2f}"
    except Exception:
        return str(v)

def ocena_metod(wyniki_dir: str):
    wyniki_path = Path(wyniki_dir)
    raporty = sorted([f for f in wyniki_path.glob("raport_*.json")])

    if not raporty:
        print("⚠️ Brak raportów do oceny w katalogu:", wyniki_path)
        return

    dane = []
    regulatory = set()
    modele = set()

    for plik in raporty:
        with open(plik, "r") as f:
            r = json.load(f)
        regulatory.add(r["regulator"])
        modele.add(r["model"])
        dane.append(r)

    regulatory = sorted(list(regulatory))
    modele = sorted(list(modele))

    # --- Agregacja wyników ---
    statystyki = {}
    for reg in regulatory:
        wyniki_r = [r for r in dane if r["regulator"] == reg]
        passy = [r for r in wyniki_r if r["PASS"]]
        proc_pass = 100 * len(passy) / len(wyniki_r)
        avg_iae = mean([r["metryki"]["IAE"] for r in wyniki_r])
        avg_ts = mean([r["metryki"]["czas_ustalania"] for r in wyniki_r])
        avg_mp = mean([r["metryki"]["przeregulowanie"] for r in wyniki_r])
        statystyki[reg] = {
            "pass_percent": proc_pass,
            "avg_IAE": avg_iae,
            "avg_ts": avg_ts,
            "avg_Mp": avg_mp,
        }

    najlepszy_regulator = min(statystyki.keys(), key=lambda r: statystyki[r]["avg_IAE"])

    # --- Lista modeli do wdrożenia ---
    passed_models = sorted(set([r["model"] for r in dane if r["PASS"]]))
    if passed_models:
        with open(wyniki_path / "passed_models.txt", "w") as f:
            for model in passed_models:
                f.write(model + "\n")
        print(f"✅ Utworzono listę modeli do wdrożenia: wyniki/passed_models.txt")

    # --- Wczytaj parametry regulatorów ---
    parametry_reg = []
    for reg in regulatory:
        for plik in sorted(wyniki_path.glob(f"parametry_{reg}_*.json")):
            with open(plik, "r") as f:
                d = json.load(f)
                p = d.get("parametry", {})
                parametry_reg.append({
                    "regulator": reg,
                    "metoda": d.get("metoda", "-"),
                    "Kp": _fmt(p.get("Kp")),
                    "Ti": _fmt(p.get("Ti")),
                    "Td": _fmt(p.get("Td")),
                })

    # --- Generacja HTML ---
    html = []
    html.append("<html><head><meta charset='UTF-8'>")
    html.append("<style>")
    html.append("""
    body { font-family: Arial, sans-serif; margin: 40px; }
    h1 { color: #2b547e; }
    h2 { margin-top: 40px; }
    table { border-collapse: collapse; width: 100%; margin-top: 20px; }
    th, td { border: 1px solid #ddd; padding: 8px; text-align: center; }
    th { background-color: #f2f2f2; }
    .pass { background-color: #c7f7c7; }
    .fail { background-color: #f9c0c0; }
    """)
    html.append("</style></head><body>")
    html.append("<h1>Raport walidacji regulatorów</h1>")

    # --- Szczegółowa tabela wyników ---
    html.append("<h2>Wyniki walidacji</h2>")
    html.append("<table>")
    html.append("<tr><th>Regulator</th><th>Metoda strojenia</th><th>Model</th>"
                "<th>IAE</th><th>ISE</th><th>Mp [%]</th><th>ts [s]</th><th>Status</th></tr>")
    for r in dane:
        cls = "pass" if r["PASS"] else "fail"
        m = r["metryki"]
        html.append(
            f"<tr class='{cls}'><td>{r['regulator']}</td><td>{r['metoda']}</td><td>{r['model']}</td>"
            f"<td>{_fmt(m['IAE'])}</td><td>{_fmt(m['ISE'])}</td>"
            f"<td>{_fmt(m['przeregulowanie'])}</td><td>{_fmt(m['czas_ustalania'])}</td>"
            f"<td>{'✅ PASS' if r['PASS'] else '❌ FAIL'}</td></tr>"
        )
    html.append("</table>")

    # --- Podsumowanie regulatorów ---
    html.append("<h2>Podsumowanie regulatorów</h2>")
    html.append("<table><tr><th>Regulator</th><th>% PASS</th><th>Średni IAE</th><th>Średni ts [s]</th><th>Średni Mp [%]</th></tr>")
    for reg, s in statystyki.items():
        html.append(f"<tr><td>{reg}</td><td>{s['pass_percent']:.1f}%</td>"
                    f"<td>{s['avg_IAE']:.2f}</td><td>{s['avg_ts']:.2f}</td>"
                    f"<td>{s['avg_Mp']:.2f}</td></tr>")
    html.append("</table>")
    html.append(f"<p><b>Najlepszy regulator (wg średniego IAE):</b> "
                f"<span style='color:green'>{najlepszy_regulator.upper()}</span></p>")

    # --- Parametry strojenia ---
    html.append("<h2>Parametry strojenia</h2>")
    html.append("<table><tr><th>Regulator</th><th>Metoda strojenia</th><th>Kp</th><th>Ti</th><th>Td</th></tr>")
    for p in parametry_reg:
        html.append(f"<tr><td>{p['regulator']}</td><td>{p['metoda']}</td>"
                    f"<td>{p['Kp']}</td><td>{p['Ti']}</td><td>{p['Td']}</td></tr>")
    html.append("</table>")

    html.append("</body></html>")

    raport_html = wyniki_path / "raport.html"
    with open(raport_html, "w", encoding="utf-8") as f:
        f.write("\n".join(html))

    print(f"✅ Raport HTML zapisano jako: {raport_html}")
    print(f"✅ Najlepszy regulator: {najlepszy_regulator.upper()} "
          f"(średni IAE={statystyki[najlepszy_regulator]['avg_IAE']:.2f})")

if __name__ == "__main__":
    ocena_metod("wyniki")
