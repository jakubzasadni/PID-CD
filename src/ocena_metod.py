# src/ocena_metod.py
"""
Porównuje wyniki walidacji regulatorów i generuje raport końcowy HTML.
"""

import json
import os
import glob
from jinja2 import Template

def ocena_metod(folder_wynikow="wyniki", metryka="IAE"):
    raporty = glob.glob(os.path.join(folder_wynikow, "raport_*.json"))
    if not raporty:
        print("❌ Brak raportów walidacji.")
        return

    wyniki = []
    najlepszy = None
    najlepsza_wartosc = float("inf")

    for plik in raporty:
        with open(plik, "r") as f:
            dane = json.load(f)
        dane["plik"] = os.path.basename(plik)
        wartosc = dane["metryki"].get(metryka, float("inf"))
        wyniki.append(dane)
        if wartosc < najlepsza_wartosc:
            najlepsza_wartosc = wartosc
            najlepszy = dane

    # Raport JSON
    with open(os.path.join(folder_wynikow, "najlepszy_regulator.json"), "w") as f:
        json.dump(najlepszy, f, indent=2)

    # Raport HTML
    html_template = """
    <html>
    <head>
        <meta charset="utf-8">
        <title>Raport walidacji regulatorów</title>
        <style>
            body { font-family: Arial; margin: 40px; }
            table { border-collapse: collapse; width: 100%; }
            th, td { border: 1px solid #ccc; padding: 8px; text-align: center; }
            th { background-color: #eee; }
            tr:nth-child(even) { background-color: #f9f9f9; }
        </style>
    </head>
    <body>
        <h2>Raport walidacji regulatorów</h2>
        <p><b>Liczba metod:</b> {{ wyniki|length }}</p>
        <table>
            <tr>
                <th>Metoda</th><th>Model</th><th>Regulator</th>
                <th>IAE</th><th>ISE</th><th>Przeregulowanie [%]</th><th>Czas ustalania [s]</th>
            </tr>
            {% for w in wyniki %}
            <tr {% if w==najlepszy %} style="background-color:#c6f6c6"{% endif %}>
                <td>{{ w.metoda }}</td>
                <td>{{ w.model }}</td>
                <td>{{ w.regulator }}</td>
                <td>{{ "%.3f"|format(w.metryki.IAE) }}</td>
                <td>{{ "%.3f"|format(w.metryki.ISE) }}</td>
                <td>{{ "%.1f"|format(w.metryki.przeregulowanie) }}</td>
                <td>{{ "%.1f"|format(w.metryki.czas_ustalania) }}</td>
            </tr>
            {% endfor %}
        </table>
        <p><b>Najlepsza metoda:</b> {{ najlepszy.metoda }} (IAE = {{ "%.3f"|format(najlepszy.metryki.IAE) }})</p>
    </body></html>
    """
    html = Template(html_template).render(wyniki=wyniki, najlepszy=najlepszy)

    with open(os.path.join(folder_wynikow, "raport.html"), "w", encoding="utf-8") as f:
        f.write(html)

    print(f"✅ Najlepszy regulator: {najlepszy['metoda']} (IAE={najlepsza_wartosc:.3f})")

if __name__ == "__main__":
    ocena_metod()
