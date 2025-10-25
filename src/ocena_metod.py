"""
Analiza i porównanie wyników walidacji regulatorów.
Tworzy raport HTML z kolorowym oznaczeniem PASS/FAIL,
procentem zaliczonych modeli oraz listę modeli do wdrożenia.
Porównuje regulatory (PID, PI, dwupołożeniowy) między sobą.
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

    # Agregacja wyników (średnie metryk i liczba PASS)
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

    # Wybór najlepszego regulatora
    najlepszy_regulator = min(statystyki.keys(), key=lambda r: statystyki[r]["avg_IAE"])

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

    # --- Wczytaj parametry regulatorów ---
    parametry_reg = {}
    for reg in regulatory:
        pliki_param = sorted(wyniki_path.glob(f"parametry_{reg}_*.json"))
        if not pliki_param:
            continue
        # bierzemy pierwszy plik (bo wszystkie metody dają podobne wyniki)
        with open(pliki_param[0], "r") as f:
            parametry = json.load(f)
        parametry_reg[reg] = parametry

    # --- Generacja raportu HTML ---
    html = []
    html.append("<html><head>")
    html.append("<meta charset='UTF-8'>")
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
    .summary { margin-top: 30px; font-size: 1.1em; }
    """)
    html.append("</style>")
    html.append("</head><body>")

    html.append("<h1>Raport walidacji regulatorów</h1>")

    # --- Szczegółowa tabela z wynikami wszystkich testów ---
    html.append("<h2>Wyniki walidacji poszczególnych modeli</h2>")
    html.append("<table>")
    html.append("<tr><th>Regulator</th><th>Metoda</th><th>Model</th>"
                "<th>IAE</th><th>ISE</th><th>Mp [%]</th><th>ts [s]</th><th>Status</th></tr>")

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

    # --- Podsumowanie regulatorów ---
    html.append("<div class='summary'>")
    html.append("<h2>Podsumowanie regulatorów</h2>")
    html.append("<table>")
    html.append("<tr><th>Regulator</th><th>% PASS</th><th>Średni IAE</th><th>Średni ts [s]</th><th>Średni Mp [%]</th></tr>")
    for reg, s in statystyki.items():
        html.append(f"<tr><td>{reg}</td>"
                    f"<td>{s['pass_percent']:.1f}%</td>"
                    f"<td>{s['avg_IAE']:.2f}</td>"
                    f"<td>{s['avg_ts']:.2f}</td>"
                    f"<td>{s['avg_Mp']:.1f}</td></tr>")
    html.append("</table>")
    html.append(f"<p><b>Najlepszy regulator:</b> <span style='color:green'>{najlepszy_regulator.upper()}</span></p>")
    html.append("</div>")

    # --- Parametry regulatorów ---
    html.append("<h2>Parametry wystrojonych regulatorów</h2>")
    html.append("<table><tr><th>Regulator</th><th>Parametr</th><th>Wartość</th></tr>")
    for reg, params in parametry_reg.items():
        for k, v in params.items():
            html.append(f"<tr><td>{reg}</td><td>{k}</td><td>{round(v, 2)}</td></tr>")
    html.append("</table>")

    html.append("</body></html>")

    raport_html = wyniki_path / "raport.html"
    raport_html.write_text("\n".join(html), encoding="utf-8")

    # --- Zapis JSON z wyborem najlepszego regulatora ---
    najlepszy_json = {
        "najlepszy_regulator": najlepszy_regulator,
        "statystyki": statystyki
    }
    with open(wyniki_path / "najlepszy_regulator.json", "w") as f:
        json.dump(najlepszy_json, f, indent=2)

    print(f"✅ Raport HTML zapisano jako: {raport_html}")
    print(f"✅ Najlepszy regulator: {najlepszy_regulator.upper()} "
          f"(średni IAE={statystyki[najlepszy_regulator]['avg_IAE']:.2f})")


if __name__ == "__main__":
    ocena_metod("wyniki")
