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
    src: str

def _read_json(fp: str) -> Dict[str, Any] | None:
    try:
        with open(fp, "r") as f:
            return json.load(f)
    except Exception:
        return None

def _norm(val, default=""):
    return val if isinstance(val, str) and val else default

def load_entries(wyniki_dir: str) -> List[Wpis]:
    entries: List[Wpis] = []

    # 1) Priorytet: gotowe wiersze z raport_*.json (mają emoji)
    for fp in sorted(glob.glob(os.path.join(wyniki_dir, "raport_*.json"))):
        d = _read_json(fp) or {}
        reg = _norm(d.get("regulator"), "")
        model = _norm(d.get("model"), "")
        # część generatorów używa 'key': 'reg:model' – rozbij jeśli brak pól powyżej
        if (not reg or not model) and isinstance(d.get("key"), str) and ":" in d["key"]:
            reg, model = d["key"].split(":", 1)
        emoji = _norm(d.get("emoji"), "❌")
        metrics = d.get("metrics") or {}
        entries.append(Wpis(regulator=reg, model=model, emoji=emoji, metrics=metrics, src=os.path.basename(fp)))

    # 2) Jeśli nie ma raportów, spróbuj z walidacja_*.json (zawierają PASS)
    if not entries:
        for fp in sorted(glob.glob(os.path.join(wyniki_dir, "walidacja_*.json"))):
            d = _read_json(fp) or {}
            reg = _norm(d.get("regulator"), "")
            model = _norm(d.get("model"), "")
            pass_cond = bool(d.get("PASS", False))
            met = d.get("metryki") or {}
            emoji = "✅" if pass_cond else "❌"
            entries.append(Wpis(regulator=reg, model=model, emoji=emoji, metrics=met, src=os.path.basename(fp)))

    return entries

def render_html(entries: List[Wpis], out_fp: str) -> None:
    rows = []
    if not entries:
        rows.append("<tr><td colspan='5'>Brak danych do oceny</td></tr>")
    else:
        for e in entries:
            mp = e.metrics.get("Mp", e.metrics.get("przeregulowanie", ""))
            ts = e.metrics.get("ts", e.metrics.get("czas_ustalania", ""))
            iae = e.metrics.get("IAE", "")
            rows.append(
                f"<tr>"
                f"<td>{e.emoji}</td>"
                f"<td>{e.regulator or '-'}</td>"
                f"<td>{e.model or '-'}</td>"
                f"<td>{mp}</td>"
                f"<td>{ts}</td>"
                f"<td>{iae}</td>"
                f"<td><code>{e.src}</code></td>"
                f"</tr>"
            )
    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<title>Raport walidacji</title>
<style>
table{{border-collapse:collapse}} td,th{{border:1px solid #ccc;padding:6px 10px}}
th{{background:#f6f6f6}}
</style>
</head><body>
<h2>Raport walidacji</h2>
<table>
<thead><tr><th>Wynik</th><th>Regulator</th><th>Model</th><th>Mp [%]</th><th>ts [s]</th><th>IAE</th><th>Plik</th></tr></thead>
<tbody>
{''.join(rows)}
</tbody>
</table>
</body></html>"""
    with open(out_fp, "w", encoding="utf-8") as f:
        f.write(html)

def main():
    wyniki_dir = sys.argv[1] if len(sys.argv) > 1 else "wyniki"
    os.makedirs(wyniki_dir, exist_ok=True)
    entries = load_entries(wyniki_dir)
    render_html(entries, os.path.join(wyniki_dir, "raport.html"))

if __name__ == "__main__":
    main()
