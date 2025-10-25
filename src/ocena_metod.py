"""
Analiza i porównanie wyników walidacji regulatorów.
Porównuje regulatory (PID, PI, PD, P), pokazuje metryki i parametry strojenia.
"""

import json
from pathlib import Path
from statistics import mean


def ocena_metod(wyniki_dir: str):
    wyniki_path = Path(wyniki_dir)
    raporty = sorted(wyniki_path.glob("raport_*.json"))
    if not raporty:
        print("⚠️ Brak raportów do oceny w katalogu:", wyniki_path)
        return

    # ----- wczytanie wyników -----
    dane = []
    regulatory = set()
    for plik in raporty:
        with open(plik, "r") as f:
            r = json.load(f)
        regulatory.add(r["regulator"])
        dane.append(r)
    regulatory = sorted(list(regulatory))

    # ----- agregaty per regulator -----
    stat = {}
    for reg in regulatory:
        R = [r for r in dane if r["regulator"] == reg]
        passy = [r for r in R if r["PASS"]]
        stat[reg] = {
            "pass_percent": 100 * len(passy) / len(R) if R else 0.0,
            "avg_IAE": mean([r["metryki"]["IAE"] for r in R]) if R else float("inf"),
            "avg_ts": mean([r["metryki"]["czas_ustalania"] for r in R]) if R else float("inf"),
            "avg_Mp": mean([r["metryki"]["przeregulowanie"] for r in R]) if R else float("inf"),
        }

    najlepszy = min(stat.keys(), key=lambda k: stat[k]["avg_IAE"])

    # ----- lista modeli do wdrożenia (dowolny PASS) -----
    passed_models = sorted({r["model"] for r in dane if r["PASS"]})
    if passed_models:
        (wyniki_path / "passed_models.txt").write_text("\n".join(passed_models), encoding="utf-8")
        print("✅ Utworzono listę modeli do wdrożenia:", wyniki_path / "passed_models.txt")
        print("Modele:", ", ".join(passed_models))
    else:
        print("❌ Żaden model nie spełnił progów — brak passed_models.txt")

    # ----- parametry z plików parametry_{reg}_{met}.json -----
    param_files = sorted(wyniki_path.glob("parametry_*.json"))
    param_rows = []
    for pf in param_files:
        with open(pf, "r") as f:
            blob = json.load(f)
        reg = blob.get("regulator", "nieznany")
        met = blob.get("metoda", "nieznana")
        P = blob.get("parametry", {})

        row = {"regulator": reg, "metoda": met}
        # dynamiczne pola
        for k in ["Kp", "Ti", "Td"]:
            v = P.get(k, None)
            if isinstance(v, (int, float)):
                row[k] = round(float(v), 2)
            elif v is None:
                row[k] = "-"
            else:
                row[k] = v
        param_rows.append(row)

    # ----- HTML -----
    html = []
    html += [
        "<html><head><meta charset='UTF-8'><style>",
        """
        body { font-family: Arial, sans-serif; margin: 36px; }
        h1 { color: #2b547e; }
        h2 { margin-top: 36px; }
        table { border-collapse: collapse; width: 100%; margin-top: 12px; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: center; }
        th { background-color: #f2f2f2; }
        .pass { background-color: #c7f7c7; }
        .fail { background-color: #f9c0c0; }
        """,
        "</style></head><body>",
        "<h1>Raport walidacji regulatorów</h1>",
        "<h2>Wyniki walidacji</h2>",
        "<table>",
        "<tr><th>Regulator</th><th>Metoda strojenia</th><th>Model</th><th>IAE</th><th>ISE</th><th>Mp [%]</th><th>ts [s]</th><th>Status</th></tr>"
    ]

    for r in dane:
        cls = "pass" if r["PASS"] else "fail"
        m = r["metryki"]
        html.append(
            f"<tr class='{cls}'><td>{r['regulator']}</td><td>{r['metoda']}</td><td>{r['model']}</td>"
            f"<td>{m['IAE']:.2f}</td><td>{m['ISE']:.2f}</td>"
            f"<td>{m['przeregulowanie']:.1f}</td><td>{m['czas_ustalania']:.1f}</td>"
            f"<td>{'✅ PASS' if r['PASS'] else '❌ FAIL'}</td></tr>"
        )
    html.append("</table>")

    # Podsumowanie
    html += [
        "<h2>Podsumowanie regulatorów</h2>",
        "<table><tr><th>Regulator</th><th>% PASS</th><th>Średni IAE</th><th>Średni ts [s]</th><th>Średni Mp [%]</th></tr>"
    ]
    for reg, s in stat.items():
        html.append(f"<tr><td>{reg}</td><td>{s['pass_percent']:.1f}%</td><td>{s['avg_IAE']:.2f}</td>"
                    f"<td>{s['avg_ts']:.2f}</td><td>{s['avg_Mp']:.1f}</td></tr>")
    html.append("</table>")
    html.append(f"<p><b>Najlepszy regulator (wg średniego IAE):</b> <span style='color:green'>{najlepszy.upper()}</span></p>")

    # Parametry
    html += [
        "<h2>Parametry strojenia</h2>",
        "<table><tr><th>Regulator</th><th>Metoda strojenia</th><th>Kp</th><th>Ti</th><th>Td</th></tr>"
    ]
    for row in param_rows:
        html.append(f"<tr><td>{row['regulator']}</td><td>{row['metoda']}</td>"
                    f"<td>{row.get('Kp','-')}</td><td>{row.get('Ti','-')}</td><td>{row.get('Td','-')}</td></tr>")
    html.append("</table>")

    html.append("</body></html>")

    raport_html = wyniki_path / "raport.html"
    raport_html.write_text("\n".join(html), encoding="utf-8")
    print(f"✅ Raport HTML zapisano jako: {raport_html}")
    print(f"✅ Najlepszy regulator: {najlepszy.upper()} (średni IAE={stat[najlepszy]['avg_IAE']:.2f})")


if __name__ == "__main__":
    ocena_metod("wyniki")
