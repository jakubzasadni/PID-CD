"""
Moduł do generowania raportów porównawczych metod strojenia.
Porównuje wyniki wszystkich metod (Ziegler-Nichols, siatka, optymalizacja) na jednym wykresie.
"""

import os
import json
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime
from typing import List, Dict, Any
import sys

# Dodaj katalog src do PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from konfig import pobierz_konfiguracje


def wczytaj_wyniki_strojenia(regulator: str, model: str, katalog_wyniki="wyniki") -> Dict[str, Any]:
    """
    Wczytuje wyniki strojenia dla wszystkich metod.
    
    Returns:
        Dict z kluczami: 'ziegler_nichols', 'siatka', 'optymalizacja'
        Wartości: {'parametry': {...}, 'raport': {...}, 'dostepny': bool}
    """
    metody = ['ziegler_nichols', 'siatka', 'optymalizacja']
    wyniki = {}
    
    for metoda in metody:
        # Wczytaj parametry
        json_path = os.path.join(katalog_wyniki, f"parametry_{regulator}_{metoda}.json")
        
        # Wczytaj raport walidacji
        raport_path = os.path.join(katalog_wyniki, f"raport_{regulator}_{metoda}_{model}.json")
        
        wynik = {'dostepny': False, 'parametry': None, 'raport': None}
        
        if os.path.exists(json_path):
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    wynik['parametry'] = data.get('parametry', {})
                    wynik['dostepny'] = True
            except Exception as e:
                print(f"[UWAGA] Błąd wczytywania {json_path}: {e}")
        
        if os.path.exists(raport_path):
            try:
                with open(raport_path, 'r', encoding='utf-8') as f:
                    wynik['raport'] = json.load(f)
            except Exception as e:
                print(f"[UWAGA] Błąd wczytywania {raport_path}: {e}")
        
        wyniki[metoda] = wynik
    
    return wyniki


def generuj_raport_porownawczy(regulator: str, model: str, katalog_wyniki="wyniki"):
    """
    Generuje raport porównawczy HTML porównujący wszystkie metody strojenia.
    
    Args:
        regulator: Nazwa regulatora (np. 'regulator_pid')
        model: Nazwa modelu (np. 'zbiornik_1rz')
        katalog_wyniki: Katalog z wynikami
    """
    print(f"\n[ANALIZA] Generowanie raportu porównawczego dla {regulator} na modelu {model}...")
    
    wyniki = wczytaj_wyniki_strojenia(regulator, model, katalog_wyniki)
    
    # Sprawdź czy są jakiekolwiek wyniki
    dostepne_metody = [m for m, w in wyniki.items() if w['dostepny']]
    if not dostepne_metody:
        print(f"[UWAGA] Brak dostępnych wyników dla {regulator} na modelu {model}")
        return
    
    print(f"  Znaleziono wyniki dla metod: {', '.join(dostepne_metody)}")
    
    # Przygotuj dane do porównania
    config = pobierz_konfiguracje()
    config_raport = config.pobierz_config_raportowania()
    
    # === TABELA PORÓWNAWCZA PARAMETRÓW ===
    html_content = []
    html_content.append("<html><head><meta charset='utf-8'>")
    html_content.append(f"<title>Raport porównawczy – {regulator} na {model}</title>")
    html_content.append("""
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        h1 { color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }
        h2 { color: #34495e; margin-top: 30px; }
        table { border-collapse: collapse; width: 100%; margin: 20px 0; }
        th, td { border: 1px solid #ddd; padding: 12px; text-align: left; }
        th { background: #3498db; color: white; font-weight: bold; }
        tr:nth-child(even) { background: #f9f9f9; }
        .best { background: #d4edda !important; font-weight: bold; }
        .metoda-nazwa { font-weight: bold; color: #2c3e50; }
        img { max-width: 100%; height: auto; margin: 10px 0; }
        .info-box { background: #e8f4f8; border-left: 4px solid #3498db; padding: 10px; margin: 20px 0; }
        .warning-box { background: #fff3cd; border-left: 4px solid #ffc107; padding: 10px; margin: 20px 0; }
    </style>
    """)
    html_content.append("</head><body><div class='container'>")
    html_content.append(f"<h1>[ANALIZA] Raport Porównawczy Metod Strojenia</h1>")
    html_content.append(f"<div class='info-box'>")
    html_content.append(f"<strong>Regulator:</strong> {regulator}<br>")
    html_content.append(f"<strong>Model:</strong> {model}<br>")
    html_content.append(f"<strong>Data wygenerowania:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    html_content.append(f"</div>")
    
    # === TABELA PARAMETRÓW ===
    html_content.append("<h2> Porównanie Parametrów</h2>")
    html_content.append("<table>")
    html_content.append("<tr><th>Metoda</th><th>Kp</th><th>Ti</th><th>Td</th></tr>")
    
    for metoda in ['ziegler_nichols', 'siatka', 'optymalizacja']:
        if wyniki[metoda]['dostepny']:
            params = wyniki[metoda]['parametry']
            nazwa_metody = metoda.replace('_', ' ').title()
            html_content.append(f"<tr>")
            html_content.append(f"<td class='metoda-nazwa'>{nazwa_metody}</td>")
            html_content.append(f"<td>{params.get('Kp', '-')}</td>")
            html_content.append(f"<td>{params.get('Ti', '-')}</td>")
            html_content.append(f"<td>{params.get('Td', '-')}</td>")
            html_content.append(f"</tr>")
    
    html_content.append("</table>")
    
    # === TABELA METRYK (jeśli dostępne raporty walidacji) ===
    raporty_dostepne = [m for m, w in wyniki.items() if w['raport'] is not None]
    
    if raporty_dostepne:
        html_content.append("<h2>[WYKRESY] Porównanie Metryk Jakości</h2>")
        html_content.append("<table>")
        html_content.append("<tr><th>Metoda</th><th>IAE</th><th>ISE</th><th>ITAE</th><th>Przeregulowanie [%]</th><th>Czas ustalania [s]</th><th>Czas narastania [s]</th></tr>")
        
        # Znajdź najlepsze wartości (dla podkreślenia)
        metryki_names = ['IAE', 'ISE', 'ITAE', 'przeregulowanie', 'czas_ustalania', 'czas_narastania']
        najlepsze = {m: float('inf') for m in metryki_names}
        
        for metoda in raporty_dostepne:
            raport = wyniki[metoda]['raport'] or {}
            met = raport.get('metryki', {})
            for m in metryki_names:
                val = met.get(m, float('inf'))
                if val is not None and val < najlepsze[m]:
                    najlepsze[m] = val
        
        for metoda in ['ziegler_nichols', 'siatka', 'optymalizacja']:
            if metoda in raporty_dostepne:
                raport = wyniki[metoda]['raport'] or {}
                met = raport.get('metryki', {})
                nazwa_metody = metoda.replace('_', ' ').title()
                html_content.append(f"<tr>")
                html_content.append(f"<td class='metoda-nazwa'>{nazwa_metody}</td>")
                
                for m in metryki_names:
                    val = met.get(m, '-')
                    if val != '-' and val is not None:
                        css_class = 'best' if abs(val - najlepsze[m]) < 1e-6 else ''
                        html_content.append(f"<td class='{css_class}'>{val:.4f}</td>")
                    else:
                        html_content.append(f"<td>-</td>")
                
                html_content.append(f"</tr>")
        
        html_content.append("</table>")
        html_content.append("<div class='info-box'>")
        html_content.append(" <strong>Najlepsze wartości</strong> dla każdej metryki są podświetlone na zielono.")
        html_content.append("</div>")
    
    # === WYKRESY PORÓWNAWCZE ===
    if raporty_dostepne:
        html_content.append("<h2>📉 Wykresy Porównawcze</h2>")
        
        # Przygotuj dane do wykresów
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        fig.suptitle(f'Porównanie metod strojenia - {regulator} na {model}', fontsize=16, fontweight='bold')
        
        kolory = {
            'ziegler_nichols': '#e74c3c',
            'siatka': '#3498db', 
            'optymalizacja': '#2ecc71'
        }
        
        nazwy_metod = {
            'ziegler_nichols': 'Ziegler-Nichols',
            'siatka': 'Przeszukiwanie siatki',
            'optymalizacja': 'Optymalizacja numeryczna'
        }
        
        # Wykres 1: IAE, ISE, ITAE
        ax1 = axes[0, 0]
        metryki_1 = ['IAE', 'ISE', 'ITAE']
        x_pos = np.arange(len(raporty_dostepne))
        width = 0.25
        
        for i, metryka in enumerate(metryki_1):
            wartosci = [ (wyniki[m]['raport'] or {}).get('metryki', {}).get(metryka, 0) for m in raporty_dostepne]
            ax1.bar(x_pos + i*width, wartosci, width, label=metryka)
        
        ax1.set_ylabel('Wartość')
        ax1.set_title('Błędy regulacji (IAE, ISE, ITAE)')
        ax1.set_xticks(x_pos + width)
        ax1.set_xticklabels([nazwy_metod[m] for m in raporty_dostepne], rotation=15, ha='right')
        ax1.legend()
        ax1.grid(axis='y', alpha=0.3)
        
        # Wykres 2: Przeregulowanie
        ax2 = axes[0, 1]
        wartosci_mp = [ ( wyniki[m]['raport'] or {}).get('metryki', {}).get('przeregulowanie', 0) for m in raporty_dostepne]
        bars = ax2.bar(range(len(raporty_dostepne)), wartosci_mp, 
                       color=[kolory[m] for m in raporty_dostepne])
        ax2.set_ylabel('Przeregulowanie [%]')
        ax2.set_title('Przeregulowanie')
        ax2.set_xticks(range(len(raporty_dostepne)))
        ax2.set_xticklabels([nazwy_metod[m] for m in raporty_dostepne], rotation=15, ha='right')
        ax2.grid(axis='y', alpha=0.3)
        
        # Wykres 3: Czasy (ustalania i narastania)
        ax3 = axes[1, 0]
        ts_vals = [ ( wyniki[m]['raport'] or {}).get('metryki', {}).get('czas_ustalania', 0) for m in raporty_dostepne]
        tr_vals = [ ( wyniki[m]['raport'] or {}).get('metryki', {}).get('czas_narastania', 0) for m in raporty_dostepne]
        
        x_pos = np.arange(len(raporty_dostepne))
        width = 0.35
        ax3.bar(x_pos - width/2, ts_vals, width, label='Czas ustalania', alpha=0.8)
        ax3.bar(x_pos + width/2, tr_vals, width, label='Czas narastania', alpha=0.8)
        ax3.set_ylabel('Czas [s]')
        ax3.set_title('Dynamika odpowiedzi')
        ax3.set_xticks(x_pos)
        ax3.set_xticklabels([nazwy_metod[m] for m in raporty_dostepne], rotation=15, ha='right')
        ax3.legend()
        ax3.grid(axis='y', alpha=0.3)
        
        # Wykres 4: Porównanie parametrów Kp
        ax4 = axes[1, 1]
        kp_vals = [wyniki[m]['parametry'].get('Kp', 0) for m in dostepne_metody]
        bars = ax4.bar(range(len(dostepne_metody)), kp_vals,
                       color=[kolory[m] for m in dostepne_metody])
        ax4.set_ylabel('Wartość Kp')
        ax4.set_title('Porównanie parametru Kp')
        ax4.set_xticks(range(len(dostepne_metody)))
        ax4.set_xticklabels([nazwy_metod[m] for m in dostepne_metody], rotation=15, ha='right')
        ax4.grid(axis='y', alpha=0.3)
        
        plt.tight_layout()
        
        wykres_path = os.path.join(katalog_wyniki, f"porownanie_{regulator}_{model}.{config_raport['format_wykresow']}")
        plt.savefig(wykres_path, dpi=config_raport['dpi'])
        plt.close()
        
        html_content.append(f"<img src='porownanie_{regulator}_{model}.{config_raport['format_wykresow']}' alt='Wykresy porównawcze'>")
        print(f"  [OK] Zapisano wykresy: {wykres_path}")
    
    # === WNIOSKI ===
    if raporty_dostepne:
        html_content.append("<h2> Wnioski</h2>")
        
        # Znajdź najlepszą metodę wg IAE
        najlepsza_metoda = min(raporty_dostepne, 
                          key=lambda m: (wyniki[m]['raport'] or {}).get('metryki', {}).get('IAE', float('inf')))
        najlepszy_IAE = (wyniki[najlepsza_metoda]['raport'] or {}).get('metryki', {}).get('IAE', float('inf'))
        
        html_content.append("<div class='info-box'>")
        html_content.append(f"<strong>Najlepsza metoda (wg IAE):</strong> {nazwy_metod[najlepsza_metoda]}<br>")
        html_content.append(f"<strong>IAE:</strong> {najlepszy_IAE:.4f}<br>")
        
        # Porównaj z innymi metodami
        html_content.append("<br><strong>Porównanie z innymi:</strong><ul>")
        for metoda in raporty_dostepne:
            if metoda != najlepsza_metoda:
                iae = (wyniki[metoda]['raport'] or {}).get('metryki', {}).get('IAE', 0)
                roznica = ((iae - najlepszy_IAE) / najlepszy_IAE) * 100
                html_content.append(f"<li>{nazwy_metod[metoda]}: IAE={iae:.4f} (+{roznica:.1f}%)</li>")
        html_content.append("</ul>")
        html_content.append("</div>")
    
    html_content.append("</div></body></html>")
    
    # Zapisz raport
    html_path = os.path.join(katalog_wyniki, f"raport_porownawczy_{regulator}_{model}.html")
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(html_content))
    
    print(f"[OK] Zapisano raport porównawczy: {html_path}")
    return html_path


if __name__ == "__main__":
    # Test
    import sys
    if len(sys.argv) > 2:
        generuj_raport_porownawczy(sys.argv[1], sys.argv[2])
    else:
        print("Użycie: python raport_porownawczy.py <regulator> <model>")
        print("Przykład: python raport_porownawczy.py regulator_pid zbiornik_1rz")
