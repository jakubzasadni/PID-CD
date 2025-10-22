"""
Analiza i porównanie wyników walidacji regulatorów.
Tworzy raport HTML z kolorowym oznaczeniem PASS/FAIL,
procentem zaliczonych modeli, tabelą parametrów PID
oraz listę modeli do wdrożenia.
"""

import os
import json
from pathlib import Path
from statistics import mean

def ocena_metod(wyniki_dir: str):
    """
    Przetwarza raporty z walidacji i generuje zbiorczy raport HTML + listę modeli do wdrożenia.
    """
    wyniki_path = Path(wyniki_dir)
    raporty = sorted([f for f in wyniki_path.glob("raport_*.json")])

    if not raporty:
        print("⚠️ Brak raportów do oceny w katalogu:", wyniki_path)
        return

    dane = []
    metody = set()
    modele = set()

    for plik in raporty:
        with open(plik, "r") as f:
            r = json.load(f)
        metody.add(r["metoda"])
        modele.add(r["model"])
        dane.append(r)

    metody = sorted(list(metody))
    modele = sorted(list(modele))

    # Agregacja wyników (średnie metryk i liczba PASS)
    statystyki = {}
    for m in metody:
        wyniki_m = [r for r in dane if r["metoda"] == m]
        passy = [r for r in wyniki_m if r["PASS"]]
        proc_pass = 100 * len(passy) / len(wyniki_m)
        avg_iae = mean([r["metryki"]["IAE"] for r in wyniki_m])
        statystyki[m] = {
            "pass_percent": proc_pass,
            "avg_IAE": avg_iae
        }

    # Wybór najlepszego regulatora
    najlepsza_metoda = min(statystyki.keys(), key=lambda m: statystyki[m]["avg_IAE"])

    # --- Tworzenie listy modeli do wdrożenia ---
    passed_models = sorted(set([r["model"] for r in dane if r["PASS"]]))
    passed_models_path = wyniki_path / "passed_models.txt"

    if passed_models:
        with open(passed_models_path, "w") as f:
            for model in passed_models:
                f.write(model + "\n")
        print(f"✅ Utworzono listę modeli do wdrożenia: {passed_models_path}")
        print("Modele:", ", ".join(passed_models))
    else:
        print("❌ Żaden model nie spełnił progów jakości — plik passed_models.txt nie zostanie utworzony.")

    # --- Wczytaj parametry PID i raporty strojenia ---
    parametry_pid = {}
    raporty_strojenia = {}

    for plik in wyniki_path.glob("parametry_*.json"):
        metoda = plik.stem.replace("parametry_", "")
        try:
            with open(plik, "r") as f:
                parametry_pid[metoda] = json.load(f)
        except Exception:
            parametry_pid[metoda] = {}

    for plik in wyniki_path.glob("raport_strojenie_*.html"):
        metoda = plik.stem.replace("raport_strojenie_", "")
        raporty_strojenia[metoda] = plik.name

    # --- Generacja raportu HTML ---
    html = []
    html.append("<html><head>")
    html.append("<meta charset='UTF-8'>")
    html.append("<style>")
    html.append("""
    body { font-family: Arial, sans-serif; margin: 40px; }
    h1 { color: #2b547e; }
    table { border-collapse: collapse; width: 100%; margin-top: 20px; }
    th, td { border: 1px solid #ddd; padding: 8px; text-align: center; }
    th { background-color: #f2f2f2; }
    a { color: #2b547e; text-decoration: none; }
    a:hover { text-decoration: underline; }
    .pass { background-color: #c7f7c7; }
    .fail { background-color: #f9c0c0; }
    .summary { margin-top: 30px; font-size: 1.1em; }
    """)
    html.append("</style>")
    html.append("</head><body>")
    html.append("<h1>Raport walidacji regulatorów</h1>")

    # --- Główna tabela wyników walidacji ---
    html.append("<h2>📊 Wyniki walidacji</h2>")
    html.append("<table>")
    html.append("<tr><th>Metoda</th><th>Model</th><th>IAE</th><th>ISE</th><th>Mp [%]</th><th>ts [s]</th><th>Status</th></tr>")

    for r in dane:
        cls = "pass" if r["PASS"] else "fail"
        m = r["metryki"]
        html.append(
            f"<tr class='{cls}'><td>{r['metoda']}</td><td>{r['model']}</td>"
            f"<td>{m['IAE']:.2f}</td><td>{m['ISE']:.2f}</td>"
            f"<td>{m['przeregulowanie']:.1f}</td><td>{m['czas_ustalania']:.1f}</td>"
            f"<td>{'✅ PASS' if r['PASS'] else '❌ FAIL'}</td></tr>"
        )

    html.append("</table>")

    # --- Tabela z parametrami PID ---
    html.append("<h2>⚙️ Parametry strojenia PID</h2>")
    html.append("<table>")
    html.append("<tr><th>Metoda</th><th>Kp</th><th>Ti</th><th>Td</th><th>Raport strojenia</th></tr>")

    for metoda, p in parametry_pid.items():
        kp = p.get("Kp", "-")
        ti = p.get("Ti", "-")
        td = p.get("Td", "-")
        raport_link = raporty_strojenia.get(metoda)
        link_html = f"<a href='{raport_link}' target='_blank'>📄 Otwórz</a>" if raport_link else "-"
        html.append(f"<tr><td>{metoda}</td><td>{kp}</td><td>{ti}</td><td>{td}</td><td>{link_html}</td></tr>")

    html.append("</table>")

    # --- Podsumowanie metod ---
    html.append("<div class='summary'>")
    html.append("<h2>📈 Podsumowanie metod</h2>")
    html.append("<table>")
    html.append("<tr><th>Metoda</th><th>% PASS</th><th>Średni IAE</th><th>Raport strojenia</th></tr>")

    for m, s in statystyki.items():
        raport_link = raporty_strojenia.get(m)
        link_html = f"<a href='{raport_link}' target='_blank'>📄</a>" if raport_link else "-"
        html.append(f"<tr><td>{m}</td><td>{s['pass_percent']:.1f}%</td><td>{s['avg_IAE']:.2f}</td><td>{link_html}</td></tr>")

    html.append("</table>")
    html.append(f"<p><b>Najlepszy regulator:</b> <span style='color:green'>{najlepsza_metoda.upper()}</span></p>")
    html.append("</div>")

    html.append("</body></html>")

    raport_html = wyniki_path / "raport.html"
    raport_html.write_text("\n".join(html), encoding="utf-8")

    # --- zapis JSON z wyborem najlepszego regulatora ---
    najlepszy_json = {
        "najlepszy_regulator": najlepsza_metoda,
        "statystyki": statystyki
    }
    with open(wyniki_path / "najlepszy_regulator.json", "w") as f:
        json.dump(najlepszy_json, f, indent=2)

    print(f"✅ Raport HTML zapisano jako: {raport_html}")
    print(f"✅ Najlepszy regulator: {najlepsza_metoda.upper()} "
          f"(średni IAE={statystyki[najlepsza_metoda]['avg_IAE']:.2f})")

if __name__ == "__main__":
    ocena_metod("wyniki")
