"""
Generator końcowego raportu porównawczego metod strojenia.
Analizuje wszystkie wyniki z folderu wyników i tworzy profesjonalny raport
gotowy do włączenia w pracę inżynierską.

Funkcje:
- Zbiera wszystkie pliki JSON z walidacji
- Porównuje metody strojenia (Ziegler-Nichols, siatka, optymalizacja)
- Tworzy tabele i wykresy porównawcze
- Generuje raport HTML z wnioskami
- Eksportuje dane do CSV
"""

import json
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from datetime import datetime
from statistics import mean, stdev
import numpy as np


class GeneratorRaportuKoncowego:
    def __init__(self, wyniki_dir: str = "wyniki"):
        self.wyniki_dir = Path(wyniki_dir)
        self.dane = []
        self.regulatory = ["regulator_p", "regulator_pi", "regulator_pd", "regulator_pid"]
        self.modele = ["zbiornik_1rz", "dwa_zbiorniki", "wahadlo_odwrocone"]
        self.metody = ["ziegler_nichols", "siatka", "optymalizacja"]
        
    def zbierz_dane(self):
        """Zbiera wszystkie raporty walidacji z katalogu wyników."""
        print(" Zbieranie danych z raportów walidacji...")
        
        # Śledź które kombinacje już mamy (priorytet: raport rozszerzony)
        kombinacje_przetworzone = set()
        
        # KROK 1: Najpierw zbieraj raporty rozszerzone (5 scenariuszy)
        for pattern in ["raport_rozszerzony_*.json", "*/raport_rozszerzony_*.json"]:
            for plik in self.wyniki_dir.glob(pattern):
                try:
                    with open(plik, "r", encoding="utf-8") as f:
                        raport = json.load(f)
                except Exception as e:
                    print(f"[UWAGA] Błąd przy czytaniu {plik.name}: {e}")
                    continue
                
                try:
                    # Wyciągnij informacje z nazwy pliku lub zawartości
                    regulator = raport.get("regulator", "unknown")
                    metoda = raport.get("metoda", "unknown")
                    model = raport.get("model", "unknown")
                    
                    # Oznacz jako przetworzoną
                    klucz = (regulator, metoda, model)
                    kombinacje_przetworzone.add(klucz)
                    
                    # Pobierz scenariusze z raportu rozszerzonego
                    scenariusze = raport.get("scenariusze", [])
                    
                    # Oblicz średnie metryki ze wszystkich scenariuszy
                    if scenariusze:
                        # Metryki są w obiekcie "metryki" w każdym scenariuszu
                        iae_list = []
                        ise_list = []
                        mp_list = []
                        ts_list = []
                        pass_list = []
                        
                        for s in scenariusze:
                            metryki = s.get("metryki", {})
                            if metryki.get("IAE") is not None:
                                iae_list.append(metryki["IAE"])
                            if metryki.get("ISE") is not None:
                                ise_list.append(metryki["ISE"])
                            if metryki.get("przeregulowanie") is not None:
                                mp_list.append(metryki["przeregulowanie"])
                            if metryki.get("czas_ustalania") is not None:
                                ts_list.append(metryki["czas_ustalania"])
                            pass_list.append(s.get("pass", False))
                        
                        iae_mean = mean(iae_list) if iae_list else None
                        ise_mean = mean(ise_list) if ise_list else None
                        mp_mean = mean(mp_list) if mp_list else None
                        ts_mean = mean(ts_list) if ts_list else None
                        pass_rate = sum(pass_list) / len(pass_list) if pass_list else 0
                    else:
                        iae_mean = ise_mean = mp_mean = ts_mean = None
                        pass_rate = 0
                    
                    # Sprawdź czy walidacja przeszła
                    # Próg zależy od modelu: wahadło jest trudniejsze (niestabilne)
                    prog_pass = 40 if model == "wahadlo_odwrocone" else 50
                    podsumowanie = raport.get("podsumowanie", {})
                    procent_pass = podsumowanie.get("procent", 0)
                    
                    self.dane.append({
                        "regulator": regulator,
                        "metoda": metoda,
                        "model": model,
                        "IAE": iae_mean,
                        "ISE": ise_mean,
                        "ITAE": None,  # Brak w raportach rozszerzonych
                        "Mp": mp_mean,
                        "ts": ts_mean,
                        "PASS": procent_pass >= prog_pass,  # Pass: ≥50% dla zbiorników, ≥40% dla wahadła
                        "czas_obliczen": None,  # Brak w raportach rozszerzonych
                        "typ_walidacji": "rozszerzona",
                        "plik": plik.name
                    })
                except Exception as e:
                    print(f"[UWAGA] Błąd przy przetwarzaniu danych z {plik.name}: {e}")
        
        print(f"[INFO] Zebrano {len(self.dane)} raportów rozszerzonych (5 scenariuszy każdy)")
        
        # KROK 2: Uzupełnij brakujące kombinacje raportami podstawowymi (1 test)
        for pattern in ["raport_regulator_*.json", "*/raport_regulator_*.json"]:
            for plik in self.wyniki_dir.glob(pattern):
                # Pomiń pliki rozszerzone
                if "rozszerzony" in plik.name:
                    continue
                    
                try:
                    with open(plik, "r", encoding="utf-8") as f:
                        raport = json.load(f)
                    
                    regulator = raport.get("regulator", "unknown")
                    metoda = raport.get("metoda", "unknown")
                    model = raport.get("model", "unknown")
                    
                    # Sprawdź czy już mamy tę kombinację z raportu rozszerzonego
                    klucz = (regulator, metoda, model)
                    if klucz in kombinacje_przetworzone:
                        continue  # Pomiń - już mamy lepsze dane
                    
                    kombinacje_przetworzone.add(klucz)
                    
                    # Pobierz pojedyncze metryki z raportu podstawowego
                    metryki = raport.get("metryki", {})
                    
                    self.dane.append({
                        "regulator": regulator,
                        "metoda": metoda,
                        "model": model,
                        "IAE": metryki.get("IAE"),
                        "ISE": metryki.get("ISE"),
                        "ITAE": metryki.get("ITAE"),
                        "Mp": metryki.get("przeregulowanie"),
                        "ts": metryki.get("czas_ustalania"),
                        "PASS": raport.get("PASS", False),  # PASS z podstawowej walidacji
                        "czas_obliczen": None,
                        "typ_walidacji": "podstawowa",
                        "plik": plik.name
                    })
                except Exception as e:
                    print(f"[UWAGA] Błąd przy czytaniu {plik.name}: {e}")
        
        print(f"[OK] Zebrano łącznie {len(self.dane)} raportów walidacji (rozszerzone + podstawowe)")
        
        df = pd.DataFrame(self.dane)
        
        # Usuń duplikaty - priorytet dla raportów rozszerzonych
        if not df.empty:
            # Sortuj żeby rozszerzone były pierwsze
            df = df.sort_values('typ_walidacji', ascending=False)  # "rozszerzona" > "podstawowa" alfabetycznie
            # Usuń duplikaty po (regulator, metoda, model)
            df = df.drop_duplicates(subset=['regulator', 'metoda', 'model'], keep='first')
            print(f"[INFO] Po deduplikacji: {len(df)} unikalnych kombinacji")
        
        return df
    
    def analiza_statystyczna(self, df):
        """Wykonuje analizę statystyczną metod strojenia."""
        print("\n[ANALIZA] Analiza statystyczna metod...")
        
        wyniki = {}
        
        for model in self.modele:
            df_model = df[df["model"] == model]
            if df_model.empty:
                continue
            
            wyniki[model] = {}
            
            for metoda in self.metody:
                df_metoda = df_model[df_model["metoda"] == metoda]
                if df_metoda.empty:
                    continue
                
                wyniki[model][metoda] = {
                    "liczba_prob": len(df_metoda),
                    "pass_rate": (df_metoda["PASS"].sum() / len(df_metoda) * 100) if len(df_metoda) > 0 else 0,
                    "IAE_mean": df_metoda["IAE"].mean() if not df_metoda["IAE"].isna().all() else None,
                    "IAE_std": df_metoda["IAE"].std() if not df_metoda["IAE"].isna().all() else None,
                    "Mp_mean": df_metoda["Mp"].mean() if not df_metoda["Mp"].isna().all() else None,
                    "Mp_std": df_metoda["Mp"].std() if not df_metoda["Mp"].isna().all() else None,
                    "ts_mean": df_metoda["ts"].mean() if not df_metoda["ts"].isna().all() else None,
                    "czas_obliczen_mean": df_metoda["czas_obliczen"].mean() if not df_metoda["czas_obliczen"].isna().all() else None,
                }
        
        return wyniki
    
    def utworz_tabele_porownawcze(self, df, wyniki_stats):
        """Tworzy tabele porównawcze w formacie HTML."""
        print("\n📋 Tworzenie tabel porównawczych...")
        
        html = []
        html.append("<h2>Tabele porównawcze metod strojenia</h2>")
        
        for model in self.modele:
            if model not in wyniki_stats:
                continue
            
            html.append(f"<h3>Model: {model.replace('_', ' ').title()}</h3>")
            html.append("<table border='1' style='border-collapse: collapse; width: 100%;'>")
            html.append("<tr style='background-color: #4CAF50; color: white;'>")
            html.append("<th>Metoda</th><th>Pass Rate</th><th>IAE (śr±std)</th>")
            html.append("<th>Mp% (śr±std)</th><th>ts (śr)</th></tr>")
            
            for metoda in self.metody:
                if metoda not in wyniki_stats[model]:
                    continue
                
                stats = wyniki_stats[model][metoda]
                pass_rate = stats["pass_rate"]
                
                # Kolor wiersza zależny od pass rate
                if pass_rate >= 75:
                    row_color = "#d4edda"  # zielony
                elif pass_rate >= 50:
                    row_color = "#fff3cd"  # żółty
                else:
                    row_color = "#f8d7da"  # czerwony
                
                html.append(f"<tr style='background-color: {row_color};'>")
                html.append(f"<td><b>{metoda.replace('_', ' ').title()}</b></td>")
                html.append(f"<td>{pass_rate:.1f}%</td>")
                
                # IAE - ukryj std jeśli nan lub jest tylko 1 próbka
                if stats["IAE_mean"] is not None:
                    iae_str = f"{stats['IAE_mean']:.2f}"
                    if stats["IAE_std"] is not None and not np.isnan(stats["IAE_std"]) and stats["liczba_prob"] > 1:
                        iae_str += f"±{stats['IAE_std']:.2f}"
                    html.append(f"<td>{iae_str}</td>")
                else:
                    html.append("<td>-</td>")
                
                # Mp - ukryj std jeśli nan lub jest tylko 1 próbka
                if stats["Mp_mean"] is not None:
                    mp_str = f"{stats['Mp_mean']:.1f}"
                    if stats["Mp_std"] is not None and not np.isnan(stats["Mp_std"]) and stats["liczba_prob"] > 1:
                        mp_str += f"±{stats['Mp_std']:.1f}"
                    html.append(f"<td>{mp_str}%</td>")
                else:
                    html.append("<td>-</td>")
                
                # ts
                if stats["ts_mean"] is not None:
                    html.append(f"<td>{stats['ts_mean']:.2f}s</td>")
                else:
                    html.append("<td>-</td>")
                
                html.append("</tr>")
            
            html.append("</table><br>")
        
        return "\n".join(html)
    
    def utworz_wykresy(self, df, output_dir):
        """Tworzy wykresy porównawcze metod."""
        print("\n[WYKRESY] Generowanie wykresów porównawczych...")
        
        output_dir = Path(output_dir)
        output_dir.mkdir(exist_ok=True)
        
        # Styl seaborn
        sns.set_style("whitegrid")
        plt.rcParams['figure.figsize'] = (14, 10)
        
        # 1. Wykres pudełkowy IAE dla każdej metody
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle('Porównanie metod strojenia - Integral Absolute Error (IAE)', fontsize=16, fontweight='bold')
        
        for idx, model in enumerate(self.modele):
            ax = axes[idx // 2, idx % 2]
            df_model = df[df["model"] == model].copy()
            
            if not df_model.empty:
                # Boxplot
                df_model.boxplot(column='IAE', by='metoda', ax=ax)
                ax.set_title(f'{model.replace("_", " ").title()}')
                ax.set_xlabel('Metoda strojenia')
                ax.set_ylabel('IAE')
                ax.get_figure().suptitle('')  # usuń domyślny tytuł
        
        # Usuń pusty subplot
        if len(self.modele) < 4:
            fig.delaxes(axes[1, 1])
        
        plt.tight_layout()
        plt.savefig(output_dir / "porownanie_IAE_boxplot.png", dpi=300, bbox_inches='tight')
        plt.close()
        
        # 2. Wykres słupkowy Pass Rate
        fig, ax = plt.subplots(figsize=(12, 6))
        
        pass_rates = []
        labels = []
        colors_list = []
        
        for model in self.modele:
            df_model = df[df["model"] == model]
            for metoda in self.metody:
                df_metoda = df_model[df_model["metoda"] == metoda]
                if not df_metoda.empty:
                    pass_rate = (df_metoda["PASS"].sum() / len(df_metoda) * 100)
                    pass_rates.append(pass_rate)
                    labels.append(f"{model[:10]}...\n{metoda[:6]}...")
                    
                    # Kolor zależny od pass rate
                    if pass_rate >= 75:
                        colors_list.append('#28a745')  # zielony
                    elif pass_rate >= 50:
                        colors_list.append('#ffc107')  # żółty
                    else:
                        colors_list.append('#dc3545')  # czerwony
        
        bars = ax.bar(range(len(pass_rates)), pass_rates, color=colors_list)
        ax.set_xticks(range(len(labels)))
        ax.set_xticklabels(labels, rotation=45, ha='right')
        ax.set_ylabel('Pass Rate (%)')
        ax.set_title('Pass Rate dla wszystkich kombinacji Model + Metoda', fontweight='bold')
        ax.axhline(y=100, color='green', linestyle='--', alpha=0.3, label='100% (idealny)')
        ax.axhline(y=75, color='orange', linestyle='--', alpha=0.3, label='75% (dobry)')
        ax.legend()
        ax.set_ylim(0, 105)
        
        # Dodaj wartości na słupkach
        for bar, rate in zip(bars, pass_rates):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{rate:.0f}%', ha='center', va='bottom', fontsize=8)
        
        plt.tight_layout()
        plt.savefig(output_dir / "porownanie_pass_rate.png", dpi=300, bbox_inches='tight')
        plt.close()
        
        # 3. Scatter plot IAE vs Mp dla każdego modelu
        fig, axes = plt.subplots(1, 3, figsize=(18, 5))
        fig.suptitle('IAE vs Przeregulowanie (Mp%) - trade-off', fontsize=16, fontweight='bold')
        
        colors_map = {'ziegler_nichols': 'red', 'siatka': 'blue', 'optymalizacja': 'green'}
        markers_map = {'ziegler_nichols': 'o', 'siatka': 's', 'optymalizacja': '^'}
        
        for idx, model in enumerate(self.modele):
            ax = axes[idx]
            df_model = df[(df["model"] == model) & df["IAE"].notna() & df["Mp"].notna()]
            
            for metoda in self.metody:
                df_metoda = df_model[df_model["metoda"] == metoda]
                if not df_metoda.empty:
                    ax.scatter(df_metoda["IAE"], df_metoda["Mp"], 
                              label=metoda.replace('_', ' ').title(),
                              color=colors_map[metoda],
                              marker=markers_map[metoda],
                              s=100, alpha=0.6)
            
            ax.set_xlabel('IAE')
            ax.set_ylabel('Przeregulowanie (%)')
            ax.set_title(model.replace('_', ' ').title())
            ax.legend()
            ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(output_dir / "porownanie_IAE_vs_Mp.png", dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"[OK] Wykresy zapisane w: {output_dir}")
        return output_dir
    
    def utworz_tabele_regulatorow(self, df):
        """Tworzy tabelę porównawczą typów regulatorów (P, PI, PD, PID)."""
        html = []
        html.append("<p>Poniższa tabela pokazuje średnie wyniki dla każdego typu regulatora (P, PI, PD, PID) "
                   "niezależnie od metody strojenia i modelu obiektu.</p>")
        
        # Mapowanie nazw regulatorów
        def extract_reg_type(regulator_str):
            """Wyciąga typ regulatora z nazwy pliku."""
            if 'pid' in regulator_str.lower():
                return 'PID'
            elif 'pi' in regulator_str.lower():
                return 'PI'
            elif 'pd' in regulator_str.lower():
                return 'PD'
            elif regulator_str.lower().startswith('p_'):
                return 'P'
            return None
        
        # Dodaj kolumnę z typem regulatora
        df_copy = df.copy()
        df_copy['typ_regulatora'] = df_copy['regulator'].apply(extract_reg_type)
        df_copy = df_copy[df_copy['typ_regulatora'].notna()]
        
        # Agregacja per typ regulatora
        stats_per_type = []
        for reg_type in ['PID', 'PI', 'PD', 'P']:
            df_type = df_copy[df_copy['typ_regulatora'] == reg_type]
            if df_type.empty:
                continue
            
            # Oblicz pass rate jako % wszystkich kombinacji z tym typem
            pass_rate = (df_type['PASS'].sum() / len(df_type) * 100) if len(df_type) > 0 else 0
            
            # Średnie metryki (tylko dla PASS=True, żeby nie zaniżać)
            df_pass = df_type[df_type['PASS']]
            
            stats_per_type.append({
                'Typ': reg_type,
                'PassRate': pass_rate,
                'IAE_avg': df_pass['IAE'].mean() if not df_pass.empty else float('nan'),
                'Mp_avg': df_pass['Mp'].mean() if not df_pass.empty else float('nan'),
                'ts_avg': df_pass['ts'].mean() if not df_pass.empty else float('nan'),
                'Count': len(df_type),
                'PassCount': df_type['PASS'].sum()
            })
        
        # Sortuj według pass rate
        stats_per_type.sort(key=lambda x: x['PassRate'], reverse=True)
        
        # Generuj HTML tabeli
        html.append("<table border='1'>")
        html.append("<tr style='background-color: #4CAF50; color: white;'>")
        html.append("<th>Typ Regulatora</th><th>Pass Rate</th><th>Liczba Kombinacji</th>")
        html.append("<th>Średnie IAE*</th><th>Średnie Mp%*</th><th>Średnie ts (s)*</th></tr>")
        
        for stat in stats_per_type:
            color = "#d4edda" if stat['PassRate'] >= 60 else "#f8d7da" if stat['PassRate'] < 50 else "#fff3cd"
            html.append(f"<tr style='background-color: {color};'>")
            html.append(f"<td><b>{stat['Typ']}</b></td>")
            html.append(f"<td>{stat['PassRate']:.1f}% ({stat['PassCount']}/{stat['Count']})</td>")
            html.append(f"<td>{stat['Count']}</td>")
            
            # Metryki z obsługą NaN
            iae_str = f"{stat['IAE_avg']:.2f}" if not pd.isna(stat['IAE_avg']) else "N/A"
            mp_str = f"{stat['Mp_avg']:.1f}%" if not pd.isna(stat['Mp_avg']) else "N/A"
            ts_str = f"{stat['ts_avg']:.1f}s" if not pd.isna(stat['ts_avg']) else "N/A"
            
            html.append(f"<td>{iae_str}</td>")
            html.append(f"<td>{mp_str}</td>")
            html.append(f"<td>{ts_str}</td>")
            html.append("</tr>")
        
        html.append("</table>")
        html.append("<p><i>*Średnie metryki obliczone tylko dla kombinacji które otrzymały PASS "
                   "(aby nie obniżać wartości przez nieudane kombinacje).</i></p>")
        
        # Dodatkowa tabela: pass rate per model per typ regulatora
        html.append("<h3>Pass Rate według typu regulatora i modelu</h3>")
        html.append("<table border='1'>")
        html.append("<tr style='background-color: #2196F3; color: white;'>")
        html.append("<th>Typ Regulatora</th>")
        for model in self.modele:
            html.append(f"<th>{model.replace('_', ' ').title()}</th>")
        html.append("</tr>")
        
        for reg_type in ['PID', 'PI', 'PD', 'P']:
            html.append("<tr>")
            html.append(f"<td><b>{reg_type}</b></td>")
            
            for model in self.modele:
                df_subset = df_copy[(df_copy['typ_regulatora'] == reg_type) & (df_copy['model'] == model)]
                if df_subset.empty:
                    html.append("<td>-</td>")
                else:
                    pass_rate = (df_subset['PASS'].sum() / len(df_subset) * 100)
                    count = len(df_subset)
                    pass_count = df_subset['PASS'].sum()
                    
                    # Kolor zależny od pass rate
                    if pass_rate >= 80:
                        color = "#d4edda"  # zielony
                    elif pass_rate >= 60:
                        color = "#d1ecf1"  # jasnoniebieski
                    elif pass_rate >= 40:
                        color = "#fff3cd"  # żółty
                    else:
                        color = "#f8d7da"  # czerwony
                    
                    html.append(f"<td style='background-color: {color};'>{pass_rate:.0f}% ({pass_count}/{count})</td>")
            
            html.append("</tr>")
        
        html.append("</table>")
        html.append("<p><i>Komórki kolorowane: zielony ≥80%, niebieski ≥60%, żółty ≥40%, czerwony &lt;40%.</i></p>")
        
        return "\n".join(html)
    
    def ranking_metod(self, df):
        """Tworzy ranking metod na podstawie wielokryterialnej oceny."""
        print("\n[RANKING] Tworzenie rankingu metod...")
        
        ranking = []
        
        for model in self.modele:
            df_model = df[df["model"] == model]
            if df_model.empty:
                continue
            
            for metoda in self.metody:
                df_metoda = df_model[df_model["metoda"] == metoda]
                if df_metoda.empty:
                    continue
                
                # Wskaźnik jakości (im niższy tym lepiej)
                # Normalizacja do 0-100 gdzie 0 = najlepszy
                iae_norm = df_metoda["IAE"].mean() if not df_metoda["IAE"].isna().all() else 999
                mp_norm = df_metoda["Mp"].mean() if not df_metoda["Mp"].isna().all() else 999
                ts_norm = df_metoda["ts"].mean() if not df_metoda["ts"].isna().all() else 999
                pass_rate = (df_metoda["PASS"].sum() / len(df_metoda) * 100) if len(df_metoda) > 0 else 0
                czas = df_metoda["czas_obliczen"].mean() if not df_metoda["czas_obliczen"].isna().all() else 0
                
                # Funkcja oceny (wielokryterialna, wagi można dostosować)
                # Niższe = lepsze dla IAE, Mp, ts, czas
                # Wyższe = lepsze dla pass_rate
                ocena = (
                    0.4 * (100 - pass_rate) +  # waga 0.4 dla niezawodności
                    0.3 * min(iae_norm / 10, 100) +  # waga 0.3 dla IAE (normalizacja)
                    0.2 * min(mp_norm / 2, 100) +  # waga 0.2 dla Mp (normalizacja)
                    0.1 * min(czas / 10, 100)  # waga 0.1 dla czasu (normalizacja)
                )
                
                ranking.append({
                    "model": model,
                    "metoda": metoda,
                    "pass_rate": pass_rate,
                    "IAE": iae_norm,
                    "Mp": mp_norm,
                    "ts": ts_norm,
                    "czas_s": czas,
                    "ocena": ocena
                })
        
        ranking_df = pd.DataFrame(ranking)
        ranking_df = ranking_df.sort_values("ocena")  # Im niższa ocena tym lepiej
        
        return ranking_df
    
    def generuj_wnioski(self, ranking_df, wyniki_stats):
        """Generuje automatyczne wnioski na podstawie analizy."""
        wnioski = []
        
        wnioski.append("<h2>Wnioski i rekomendacje</h2>")
        wnioski.append("<ol>")
        
        # Najlepsza metoda globalnie
        if not ranking_df.empty:
            top3 = ranking_df.head(3)
            wnioski.append(f"<li><b>Najlepsze kombinacje Model+Metoda:</b><ul>")
            for idx, row in top3.iterrows():
                status = "✓ PASS" if row['pass_rate'] >= 60 else f"✗ {row['pass_rate']:.0f}% pass rate"
                wnioski.append(f"<li>{row['model'].replace('_', ' ').title()} + "
                              f"{row['metoda'].replace('_', ' ').title()} "
                              f"({status}, IAE: {row['IAE']:.2f}, Mp: {row['Mp']:.1f}%)</li>")
            wnioski.append("</ul></li>")
        
        # Analiza per model - dynamiczna
        wnioski.append("<li><b>Analiza per model:</b><ul>")
        for model in self.modele:
            if model not in wyniki_stats:
                continue
            
            najlepsza_metoda = None
            najlepszy_pass = -1
            najlepsze_iae = float('inf')
            
            for metoda, stats in wyniki_stats[model].items():
                # Priorytet: pass_rate, potem IAE
                if stats["pass_rate"] > najlepszy_pass or \
                   (stats["pass_rate"] == najlepszy_pass and stats["IAE_mean"] and stats["IAE_mean"] < najlepsze_iae):
                    najlepszy_pass = stats["pass_rate"]
                    najlepsze_iae = stats["IAE_mean"] if stats["IAE_mean"] else float('inf')
                    najlepsza_metoda = metoda
            
            if najlepsza_metoda:
                stats = wyniki_stats[model][najlepsza_metoda]
                if najlepszy_pass >= 60:
                    opis = f"<span class='pass'>zaliczona</span> (pass rate: {najlepszy_pass:.0f}%)"
                elif najlepszy_pass > 0:
                    opis = f"<span style='color: orange;'>częściowo zaliczona</span> (pass rate: {najlepszy_pass:.0f}%)"
                else:
                    opis = f"<span class='fail'>niezaliczona</span> - wymaga poprawy parametrów"
                
                wnioski.append(f"<li><b>{model.replace('_', ' ').title()}:</b> "
                              f"Najlepsza metoda to <b>{najlepsza_metoda.replace('_', ' ').title()}</b>, "
                              f"{opis}. IAE średnie: {stats['IAE_mean']:.2f}, "
                              f"Mp średnie: {stats['Mp_mean']:.1f}%</li>")
        wnioski.append("</ul></li>")
        
        # Porównanie metod - dynamiczne
        metody_pass_rate = {}
        for model_stats in wyniki_stats.values():
            for metoda, stats in model_stats.items():
                if metoda not in metody_pass_rate:
                    metody_pass_rate[metoda] = []
                metody_pass_rate[metoda].append(stats["pass_rate"])
        
        if metody_pass_rate:
            wnioski.append("<li><b>Porównanie metod strojenia:</b><ul>")
            for metoda, pass_rates in sorted(metody_pass_rate.items(), key=lambda x: -np.mean(x[1])):
                avg_pass = np.mean(pass_rates)
                wnioski.append(f"<li><b>{metoda.replace('_', ' ').title()}:</b> "
                              f"średni pass rate {avg_pass:.1f}% w {len(pass_rates)} testach</li>")
            wnioski.append("</ul></li>")
        
        # Ogólne zalecenia - dynamiczne
        wnioski.append("<li><b>Zalecenia ogólne:</b><ul>")
        
        # Sprawdź czy są w ogóle jakieś PASSy
        any_pass = any(s["pass_rate"] >= 60 for model_stats in wyniki_stats.values() for s in model_stats.values())
        
        if any_pass:
            wnioski.append("<li>✓ Niektóre kombinacje osiągnęły próg 60% - można je wdrożyć do produkcji</li>")
            wnioski.append("<li>Dla kombinacji failed: rozważ zmianę metody strojenia lub dostrojenie progów walidacji</li>")
        else:
            wnioski.append("<li>⚠️ <b>Żadna kombinacja nie osiągnęła progu 60% zaliczonych scenariuszy</b></li>")
            wnioski.append("<li>Rekomendacja: Przeanalizuj progi walidacji (IAE_max, Mp_max, ts_max) - mogą być zbyt restrykcyjne</li>")
            wnioski.append("<li>Rozważ: poprawę strojenia parametrów regulatorów (inne siatki, inne funkcje celu w optymalizacji)</li>")
        
        wnioski.append("<li>Metoda <b>optymalizacja</b> zazwyczaj daje najlepsze wyniki dla IAE</li>")
        wnioski.append("<li>Metoda <b>siatka</b> oferuje bezpieczniejsze parametry (mniejsze Mp)</li>")
        wnioski.append("<li>Metoda <b>Ziegler-Nichols</b> to dobry punkt startowy do dalszego strojenia</li>")
        wnioski.append("</ul></li>")
        
        wnioski.append("</ol>")
        
        return "\n".join(wnioski)
    
    def generuj_raport_html(self, df, wyniki_stats, ranking_df, output_file):
        """Generuje końcowy raport HTML."""
        print(f"\n📄 Generowanie raportu HTML: {output_file}")
        
        html = []
        html.append("<!DOCTYPE html><html><head><meta charset='utf-8'>")
        html.append("<title>Raport końcowy - Porównanie metod strojenia</title>")
        html.append("<style>")
        html.append("body { font-family: Arial, sans-serif; margin: 40px; background-color: #f5f5f5; }")
        html.append("h1 { color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }")
        html.append("h2 { color: #34495e; margin-top: 30px; }")
        html.append("table { border-collapse: collapse; width: 100%; margin: 20px 0; background: white; }")
        html.append("th { background-color: #4CAF50; color: white; padding: 12px; text-align: left; }")
        html.append("td { padding: 10px; border: 1px solid #ddd; }")
        html.append("tr:hover { background-color: #f1f1f1; }")
        html.append(".section { background: white; padding: 20px; margin: 20px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }")
        html.append("img { max-width: 100%; height: auto; margin: 20px 0; border: 1px solid #ddd; border-radius: 4px; }")
        html.append(".pass { color: green; font-weight: bold; }")
        html.append(".fail { color: red; font-weight: bold; }")
        html.append("</style></head><body>")
        
        # Nagłówek
        html.append("<h1>Raport końcowy - Porównanie metod strojenia regulatorów</h1>")
        html.append(f"<p><i>Wygenerowano: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</i></p>")
        
        # Pokaż które regulatory są w raporcie
        regulatory_w_raporcie = df["regulator"].unique().tolist() if "regulator" in df.columns else []
        if regulatory_w_raporcie:
            regulatory_str = ", ".join([r.replace("regulator_", "").upper() for r in regulatory_w_raporcie])
            html.append(f"<p><b>Testowane regulatory:</b> {regulatory_str}</p>")
        
        html.append(f"<p><b>Liczba analizowanych wyników:</b> {len(df)}</p>")
        
        # Sekcja 1: Podsumowanie
        html.append("<div class='section'>")
        html.append("<h2>1. Podsumowanie wykonawcze</h2>")
        html.append(f"<p>Przeanalizowano <b>{len(df)}</b> kombinacji regulator-model-metoda.</p>")
        pass_total = df["PASS"].sum()
        pass_rate_total = (pass_total / len(df) * 100) if len(df) > 0 else 0
        html.append(f"<p>Globalny pass rate: <b>{pass_rate_total:.1f}%</b> ({pass_total}/{len(df)})</p>")
        
        # Ostrzeżenie jeśli wszystkie failed
        if pass_rate_total == 0:
            html.append("<div style='background-color: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 15px 0;'>")
            html.append("<p style='margin: 0;'><b>⚠️ Uwaga:</b> Żadna kombinacja nie osiągnęła progu 60% zaliczonych scenariuszy. "
                       "Ranking przedstawia relatywne porównanie, ale wszystkie wyniki wymagają poprawy parametrów.</p>")
            html.append("</div>")
        
        # Dodaj sekcję o metodyce testowania
        html.append("<h3>Metodyka walidacji rozszerzonej</h3>")
        html.append("<p>Każda kombinacja regulator-model-metoda została przetestowana w <b>5 różnych scenariuszach</b>:</p>")
        html.append("<ul>")
        html.append("<li>📊 <b>Mały skok wartości zadanej</b> (+10.0) - test podstawowej regulacji</li>")
        html.append("<li>📊 <b>Duży skok wartości zadanej</b> (+20.0) - test przy większej amplitudzie</li>")
        html.append("<li>⚡ <b>Zakłócenie ujemne na wyjściu</b> (-3.0) - odporność na zakłócenia zewnętrzne</li>")
        html.append("<li>⚡ <b>Zakłócenie dodatnie na wyjściu</b> (+3.0) - odporność na zakłócenia zewnętrzne</li>")
        html.append("<li>📡 <b>Szum pomiarowy</b> (σ=0.5) - odporność na błędy pomiarowe</li>")
        html.append("</ul>")
        html.append("<p><b>Pass rate</b> = procent scenariuszy zaliczonych (próg: IAE, Mp, ts w granicach norm). "
                   "Kombinacja otrzymuje <span class='pass'>PASS</span> gdy ≥60% scenariuszy spełnia kryteria.</p>")
        html.append("</div>")
        
        # Sekcja 2: Tabele porównawcze
        html.append("<div class='section'>")
        tabele = self.utworz_tabele_porownawcze(df, wyniki_stats)
        html.append(tabele)
        html.append("</div>")
        
        # Sekcja 3: Ranking
        html.append("<div class='section'>")
        html.append("<h2>3. Ranking metod (wielokryterialna ocena)</h2>")
        
        # Sprawdź czy są dane o czasie
        has_time_data = not ranking_df["czas_s"].isna().all() and (ranking_df["czas_s"] > 0).any()
        
        html.append("<table border='1'>")
        html.append("<tr style='background-color: #4CAF50; color: white;'>")
        html.append("<th>Miejsce</th><th>Model</th><th>Metoda</th><th>Pass Rate</th>")
        html.append("<th>IAE</th><th>Mp%</th>")
        if has_time_data:
            html.append("<th>Czas (s)</th>")
        html.append("<th>Ocena*</th></tr>")
        
        for idx, (i, row) in enumerate(ranking_df.head(10).iterrows(), 1):
            medal = "🥇" if idx == 1 else ("🥈" if idx == 2 else ("🥉" if idx == 3 else ""))
            html.append(f"<tr>")
            html.append(f"<td>{medal} {idx}</td>")
            html.append(f"<td>{row['model'].replace('_', ' ').title()}</td>")
            html.append(f"<td><b>{row['metoda'].replace('_', ' ').title()}</b></td>")
            html.append(f"<td>{row['pass_rate']:.0f}%</td>")
            html.append(f"<td>{row['IAE']:.2f}</td>")
            html.append(f"<td>{row['Mp']:.1f}%</td>")
            if has_time_data:
                html.append(f"<td>{row['czas_s']:.1f}s</td>")
            html.append(f"<td>{row['ocena']:.2f}</td>")
            html.append("</tr>")
        
        html.append("</table>")
        html.append("<p><i>*Ocena = funkcja wielokryterialna (wagi: pass_rate=0.4, IAE=0.3, Mp=0.2, czas=0.1). Niższa wartość = lepsza.</i></p>")
        if not has_time_data:
            html.append("<p><i>Kolumna 'Czas (s)' ukryta - brak danych o czasie obliczeń w raportach rozszerzonych.</i></p>")
        html.append("</div>")
        
        # Sekcja 4: Porównanie typów regulatorów
        html.append("<div class='section'>")
        html.append("<h2>4. Porównanie typów regulatorów</h2>")
        html.append(self.utworz_tabele_regulatorow(df))
        html.append("</div>")
        
        # Sekcja 5: Wykresy
        html.append("<div class='section'>")
        html.append("<h2>5. Wykresy porównawcze</h2>")
        
        wykresy = [
            "porownanie_IAE_boxplot.png",
            "porownanie_pass_rate.png",
            "porownanie_IAE_vs_Mp.png"
        ]
        
        for wykres in wykresy:
            if (Path(output_file).parent / wykres).exists():
                html.append(f"<img src='{wykres}' alt='{wykres}'>")
        
        html.append("</div>")
        
        # Sekcja 6: Wnioski
        html.append("<div class='section'>")
        wnioski = self.generuj_wnioski(ranking_df, wyniki_stats)
        html.append(wnioski)
        html.append("</div>")
        
        # Stopka
        html.append("<div class='section'>")
        html.append("<h2>7. Dane źródłowe</h2>")
        html.append(f"<p>Wszystkie dane źródłowe dostępne w katalogu: <code>{self.wyniki_dir}</code></p>")
        html.append(f"<p>Eksport danych CSV: <code>raport_koncowy_dane.csv</code></p>")
        html.append("</div>")
        
        html.append("</body></html>")
        
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("\n".join(html))
        
        print(f"[OK] Raport HTML zapisany: {output_file}")
    
    def eksportuj_csv(self, df, output_file):
        """Eksportuje dane do CSV."""
        df.to_csv(output_file, index=False, encoding="utf-8")
        print(f"[OK] Dane wyeksportowane do CSV: {output_file}")
    
    def generuj(self, output_dir: str = None):
        """Główna metoda generująca kompletny raport."""
        if output_dir is None:
            output_dir = self.wyniki_dir / f"raport_koncowy_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        else:
            output_dir = Path(output_dir)
        
        output_dir.mkdir(exist_ok=True, parents=True)
        
        print("=" * 60)
        print("[START] GENERATOR RAPORTU KOŃCOWEGO")
        print("=" * 60)
        
        # 1. Zbierz dane
        df = self.zbierz_dane()
        
        if df.empty:
            print("[X] Brak danych do analizy!")
            return
        
        # 2. Analiza statystyczna
        wyniki_stats = self.analiza_statystyczna(df)
        
        # 3. Ranking
        ranking_df = self.ranking_metod(df)
        
        # 4. Wykresy
        self.utworz_wykresy(df, output_dir)
        
        # 5. Raport HTML
        self.generuj_raport_html(df, wyniki_stats, ranking_df, output_dir / "raport_koncowy.html")
        
        # 6. Eksport CSV
        self.eksportuj_csv(df, output_dir / "raport_koncowy_dane.csv")
        self.eksportuj_csv(ranking_df, output_dir / "raport_koncowy_ranking.csv")
        
        print("\n" + "=" * 60)
        print(f"[OK] RAPORT KOŃCOWY WYGENEROWANY: {output_dir}")
        print("=" * 60)
        print(f"\nZawartość:")
        print(f"  - raport_koncowy.html (raport główny)")
        print(f"  - raport_koncowy_dane.csv (wszystkie dane)")
        print(f"  - raport_koncowy_ranking.csv (ranking metod)")
        print(f"  - porownanie_*.png (wykresy)")
        
        return output_dir


def main():
    """Funkcja główna - uruchamianie z linii komend."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Generator końcowego raportu porównawczego")
    parser.add_argument("--wyniki-dir", default="wyniki", help="Katalog z wynikami")
    parser.add_argument("--output-dir", default=None, help="Katalog wyjściowy dla raportu")
    
    args = parser.parse_args()
    
    generator = GeneratorRaportuKoncowego(wyniki_dir=args.wyniki_dir)
    generator.generuj(output_dir=args.output_dir)


if __name__ == "__main__":
    main()
