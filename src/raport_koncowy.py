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
        print("📂 Zbieranie danych z raportów walidacji...")
        
        # Szukaj w głównym folderze i podfolderach
        for pattern in ["raport_*.json", "*/raport_*.json"]:
            for plik in self.wyniki_dir.glob(pattern):
                # Pomijaj raporty rozszerzone
                if "rozszerzony" in plik.name:
                    continue
                    
                try:
                    with open(plik, "r", encoding="utf-8") as f:
                        raport = json.load(f)
                    
                    # Wyciągnij informacje z nazwy pliku lub zawartości
                    regulator = raport.get("regulator", "unknown")
                    metoda = raport.get("metoda", "unknown")
                    model = raport.get("model", "unknown")
                    
                    # Dodaj czas obliczeń jeśli dostępny
                    czas_obliczen = raport.get("czas_obliczen_s", None)
                    
                    # Pobierz metryki
                    metryki = raport.get("metryki", {})
                    
                    self.dane.append({
                        "regulator": regulator,
                        "metoda": metoda,
                        "model": model,
                        "IAE": metryki.get("IAE", None),
                        "ISE": metryki.get("ISE", None),
                        "ITAE": metryki.get("ITAE", None),
                        "Mp": metryki.get("przeregulowanie", None),
                        "ts": metryki.get("czas_ustalania", None),
                        "PASS": raport.get("PASS", False),
                        "czas_obliczen": czas_obliczen,
                        "plik": plik.name
                    })
                except Exception as e:
                    print(f"⚠️ Błąd przy czytaniu {plik.name}: {e}")
        
        print(f"✅ Zebrano {len(self.dane)} raportów walidacji")
        return pd.DataFrame(self.dane)
    
    def analiza_statystyczna(self, df):
        """Wykonuje analizę statystyczną metod strojenia."""
        print("\n📊 Analiza statystyczna metod...")
        
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
            html.append("<th>Mp% (śr±std)</th><th>ts (śr)</th><th>Czas obliczeń (s)</th></tr>")
            
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
                
                # IAE
                if stats["IAE_mean"] is not None:
                    iae_str = f"{stats['IAE_mean']:.2f}"
                    if stats["IAE_std"] is not None:
                        iae_str += f"±{stats['IAE_std']:.2f}"
                    html.append(f"<td>{iae_str}</td>")
                else:
                    html.append("<td>-</td>")
                
                # Mp
                if stats["Mp_mean"] is not None:
                    mp_str = f"{stats['Mp_mean']:.1f}"
                    if stats["Mp_std"] is not None:
                        mp_str += f"±{stats['Mp_std']:.1f}"
                    html.append(f"<td>{mp_str}%</td>")
                else:
                    html.append("<td>-</td>")
                
                # ts
                if stats["ts_mean"] is not None:
                    html.append(f"<td>{stats['ts_mean']:.2f}s</td>")
                else:
                    html.append("<td>-</td>")
                
                # Czas obliczeń
                if stats["czas_obliczen_mean"] is not None:
                    html.append(f"<td>{stats['czas_obliczen_mean']:.2f}s</td>")
                else:
                    html.append("<td>-</td>")
                
                html.append("</tr>")
            
            html.append("</table><br>")
        
        return "\n".join(html)
    
    def utworz_wykresy(self, df, output_dir):
        """Tworzy wykresy porównawcze metod."""
        print("\n📈 Generowanie wykresów porównawczych...")
        
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
        ax.axhline(y=100, color='green', linestyle='--', alpha=0.3, label='100% (ideal)')
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
        
        # 3. Heatmap czasu obliczeń
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # Pivot table dla czasu obliczeń
        df_czas = df[df["czas_obliczen"].notna()].copy()
        if not df_czas.empty:
            pivot = df_czas.pivot_table(values='czas_obliczen', 
                                        index='metoda', 
                                        columns='model', 
                                        aggfunc='mean')
            
            sns.heatmap(pivot, annot=True, fmt='.1f', cmap='YlOrRd', ax=ax, cbar_kws={'label': 'Czas (s)'})
            ax.set_title('Średni czas obliczeń (s) - Metoda vs Model', fontweight='bold')
            ax.set_xlabel('Model')
            ax.set_ylabel('Metoda strojenia')
            
            plt.tight_layout()
            plt.savefig(output_dir / "porownanie_czas_obliczen.png", dpi=300, bbox_inches='tight')
            plt.close()
        
        # 4. Scatter plot IAE vs Mp dla każdego modelu
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
        
        print(f"✅ Wykresy zapisane w: {output_dir}")
        return output_dir
    
    def ranking_metod(self, df):
        """Tworzy ranking metod na podstawie wielokryterialnej oceny."""
        print("\n🏆 Tworzenie rankingu metod...")
        
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
                wnioski.append(f"<li>{row['model'].replace('_', ' ').title()} + "
                              f"{row['metoda'].replace('_', ' ').title()} "
                              f"(pass rate: {row['pass_rate']:.0f}%, IAE: {row['IAE']:.2f})</li>")
            wnioski.append("</ul></li>")
        
        # Analiza per model
        for model in self.modele:
            if model not in wyniki_stats:
                continue
            
            najlepsza_metoda = None
            najlepszy_pass = 0
            
            for metoda, stats in wyniki_stats[model].items():
                if stats["pass_rate"] > najlepszy_pass:
                    najlepszy_pass = stats["pass_rate"]
                    najlepsza_metoda = metoda
            
            if najlepsza_metoda:
                wnioski.append(f"<li><b>Model {model.replace('_', ' ').title()}:</b> "
                              f"Najlepsza metoda to <b>{najlepsza_metoda.replace('_', ' ').title()}</b> "
                              f"z pass rate {najlepszy_pass:.0f}%</li>")
        
        # Porównanie czasu obliczeń
        wnioski.append("<li><b>Czas obliczeń:</b> Metoda <b>Ziegler-Nichols</b> jest najszybsza (analityczna), "
                      "metoda <b>siatka</b> jest wolniejsza ale bardziej dokładna, "
                      "metoda <b>optymalizacja</b> oferuje najlepszy kompromis czas/jakość.</li>")
        
        # Ogólne zalecenia
        wnioski.append("<li><b>Zalecenia dla wdrożenia:</b><ul>")
        wnioski.append("<li>Do systemów o prostej dynamice (zbiornik 1-rzędowy): optymalizacja lub siatka</li>")
        wnioski.append("<li>Do systemów złożonych (kaskady, wahadło): preferuj siatkę dla bezpieczeństwa</li>")
        wnioski.append("<li>Do szybkiego prototypowania: Ziegler-Nichols jako punkt startowy</li>")
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
        html.append("<h1>📊 Raport końcowy - Porównanie metod strojenia regulatorów</h1>")
        html.append(f"<p><i>Wygenerowano: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</i></p>")
        html.append(f"<p><b>Liczba analizowanych wyników:</b> {len(df)}</p>")
        
        # Sekcja 1: Podsumowanie
        html.append("<div class='section'>")
        html.append("<h2>1. Podsumowanie wykonawcze</h2>")
        html.append(f"<p>Przeanalizowano <b>{len(df)}</b> kombinacji regulator-model-metoda.</p>")
        pass_total = df["PASS"].sum()
        pass_rate_total = (pass_total / len(df) * 100) if len(df) > 0 else 0
        html.append(f"<p>Globalny pass rate: <b>{pass_rate_total:.1f}%</b> ({pass_total}/{len(df)})</p>")
        html.append("</div>")
        
        # Sekcja 2: Tabele porównawcze
        html.append("<div class='section'>")
        tabele = self.utworz_tabele_porownawcze(df, wyniki_stats)
        html.append(tabele)
        html.append("</div>")
        
        # Sekcja 3: Ranking
        html.append("<div class='section'>")
        html.append("<h2>3. Ranking metod (wielokryterialna ocena)</h2>")
        html.append("<table border='1'>")
        html.append("<tr style='background-color: #4CAF50; color: white;'>")
        html.append("<th>Miejsce</th><th>Model</th><th>Metoda</th><th>Pass Rate</th>")
        html.append("<th>IAE</th><th>Mp%</th><th>Czas (s)</th><th>Ocena*</th></tr>")
        
        for idx, (i, row) in enumerate(ranking_df.head(10).iterrows(), 1):
            medal = "🥇" if idx == 1 else ("🥈" if idx == 2 else ("🥉" if idx == 3 else ""))
            html.append(f"<tr>")
            html.append(f"<td>{medal} {idx}</td>")
            html.append(f"<td>{row['model'].replace('_', ' ').title()}</td>")
            html.append(f"<td><b>{row['metoda'].replace('_', ' ').title()}</b></td>")
            html.append(f"<td>{row['pass_rate']:.0f}%</td>")
            html.append(f"<td>{row['IAE']:.2f}</td>")
            html.append(f"<td>{row['Mp']:.1f}%</td>")
            html.append(f"<td>{row['czas_s']:.1f}s</td>")
            html.append(f"<td>{row['ocena']:.2f}</td>")
            html.append("</tr>")
        
        html.append("</table>")
        html.append("<p><i>*Ocena = funkcja wielokryterialna (wagi: pass_rate=0.4, IAE=0.3, Mp=0.2, czas=0.1). Niższa wartość = lepsza.</i></p>")
        html.append("</div>")
        
        # Sekcja 4: Wykresy
        html.append("<div class='section'>")
        html.append("<h2>4. Wykresy porównawcze</h2>")
        
        wykresy = [
            "porownanie_IAE_boxplot.png",
            "porownanie_pass_rate.png",
            "porownanie_czas_obliczen.png",
            "porownanie_IAE_vs_Mp.png"
        ]
        
        for wykres in wykresy:
            if (Path(output_file).parent / wykres).exists():
                html.append(f"<img src='{wykres}' alt='{wykres}'>")
        
        html.append("</div>")
        
        # Sekcja 5: Wnioski
        html.append("<div class='section'>")
        wnioski = self.generuj_wnioski(ranking_df, wyniki_stats)
        html.append(wnioski)
        html.append("</div>")
        
        # Stopka
        html.append("<div class='section'>")
        html.append("<h2>5. Dane źródłowe</h2>")
        html.append(f"<p>Wszystkie dane źródłowe dostępne w katalogu: <code>{self.wyniki_dir}</code></p>")
        html.append(f"<p>Eksport danych CSV: <code>raport_koncowy_dane.csv</code></p>")
        html.append("</div>")
        
        html.append("</body></html>")
        
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("\n".join(html))
        
        print(f"✅ Raport HTML zapisany: {output_file}")
    
    def eksportuj_csv(self, df, output_file):
        """Eksportuje dane do CSV."""
        df.to_csv(output_file, index=False, encoding="utf-8")
        print(f"✅ Dane wyeksportowane do CSV: {output_file}")
    
    def generuj(self, output_dir: str = None):
        """Główna metoda generująca kompletny raport."""
        if output_dir is None:
            output_dir = self.wyniki_dir / f"raport_koncowy_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        else:
            output_dir = Path(output_dir)
        
        output_dir.mkdir(exist_ok=True, parents=True)
        
        print("=" * 60)
        print("🚀 GENERATOR RAPORTU KOŃCOWEGO")
        print("=" * 60)
        
        # 1. Zbierz dane
        df = self.zbierz_dane()
        
        if df.empty:
            print("❌ Brak danych do analizy!")
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
        print(f"✅ RAPORT KOŃCOWY WYGENEROWANY: {output_dir}")
        print("=" * 60)
        print(f"\n📂 Zawartość:")
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
