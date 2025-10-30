# src/ocena_metod.py
from __future__ import annotations
import os, sys, json, glob
from dataclasses import dataclass
from typing import List, Dict, Any

@dataclass
class Wpis:
    regulator: str
    model: str
    emoji: str
    metrics: Dict[str, float]
    plot: str | None
    src: str

def _read_json(fp: str) -> Dict[str, Any] | None:
    try:
        with open(fp, "r") as f:
            return json.load(f)
    except Exception:
        return None

def _norms(d: Dict[str, Any], k: str, default=""):
    v = d.get(k)
    return v if isinstance(v, str) and v else default

def load_entries(wdir: str) -> List[Wpis]:
    entries: List[Wpis] = []
    # Najpierw raport_*.json
    for fp in sorted(glob.glob(os.path.join(wdir, "raport_*.json"))):
        d = _read_json(fp) or {}
        reg = _norms(d, "regulator"); model = _norms(d, "model")
        if (not reg or not model) and isinstance(d.get("key"), str) and ":" in d["key"]:
            reg, model = d["key"].split(":", 1)
        emoji = _norms(d, "emoji", "❌")
        entries.append(Wpis(
            regulator=reg or "-", model=model or "-", emoji=emoji,
            metrics=d.get("metrics") or {}, plot=_norms(d, "plot", None),
            src=os.path.basename(fp)
        ))
    if not entries:
        for fp in sorted(glob.glob(os.path.join(wdir, "walidacja_*.json"))):
            d = _read_json(fp) or {}
            emoji = "✅" if d.get("PASS") else "❌"
            entries.append(Wpis(
                regulator=_norms(d, "regulator") or "-", model=_norms(d, "model") or "-", emoji=emoji,
                metrics=d.get("metryki") or {}, plot=_norms(d, "plot", None),
                src=os.path.basename(fp)
            ))
    return entries

def render_html(entries: List[Wpis], out_fp: str, base: str):
    def row(e: Wpis) -> str:
        mp = e.metrics.get("Mp", e.metrics.get("przeregulowanie", ""))
        ts = e.metrics.get("ts", e.metrics.get("czas_ustalania", ""))
        iae = e.metrics.get("IAE", "")
        img = f"<a href='{e.plot}'><img src='{e.plot}' style='height:68px;border:1px solid #ddd;border-radius:6px'></a>" if (e.plot and os.path.exists(os.path.join(base, e.plot))) else "—"
        return (
            f"<tr class='{'ok' if e.emoji=='✅' else 'fail'}'>"
            f"<td class='center'>{e.emoji}</td>"
            f"<td>{e.regulator}</td>"
            f"<td>{e.model}</td>"
            f"<td class='num'>{mp}</td>"
            f"<td class='num'>{ts}</td>"
            f"<td class='num'>{iae}</td>"
            f"<td>{img}</td>"
            f"<td><code>{e.src}</code></td>"
            f"</tr>"
        )

    rows = "\n".join(row(e) for e in entries) if entries else "<tr><td colspan='8'>Brak danych</td></tr>"
    html = f"""<!doctype html><html><head><meta charset="utf-8">
<title>Raport walidacji</title>
<style>
body{{font-family:Inter,Segoe UI,Arial,sans-serif;margin:24px}}
h2{{margin:0 0 12px 0}}
.badge{{display:inline-block;background:#eef;border:1px solid #ccd;padding:4px 8px;border-radius:6px;margin-right:8px}}
table{{border-collapse:collapse;width:100%}}
th,td{{border:1px solid #e3e3e3;padding:8px}}
th{{background:#fafafa}}
tr.ok{{background:#f6fff6}}
tr.fail{{background:#fff6f6}}
.num{{text-align:right}}
.center{{text-align:center}}
img{{display:block}}
.small{{color:#666;font-size:12px}}
</style>
</head><body>
<h2>Raport walidacji</h2>
<div class="small">Wygenerowano automatycznie – miniatury linkują do pełnych PNG.</div>
<table>
<thead><tr><th>Wynik</th><th>Regulator</th><th>Model</th><th>Mp [%]</th><th>ts [s]</th><th>IAE</th><th>Wykres</th><th>Plik</th></tr></thead>
<tbody>
{rows}
</tbody>
</table>
</body></html>"""
    with open(out_fp, "w", encoding="utf-8") as f:
        f.write(html)

def main():
    wdir = sys.argv[1] if len(sys.argv) > 1 else "wyniki"
    os.makedirs(wdir, exist_ok=True)
    entries = load_entries(wdir)
    render_html(entries, os.path.join(wdir, "raport.html"), wdir)

if __name__ == "__main__":
    main()
