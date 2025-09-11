import json
import pathlib

def main():
    out_dir = pathlib.Path("out")
    summary = []
    for run in out_dir.iterdir():
        if (run / "report.json").exists():
            data = json.loads((run / "report.json").read_text())
            m = data["metrics"]
            summary.append({
                "run": run.name,
                "kp": data["pid"]["kp"],
                "ti": data["pid"]["ti"],
                "overshoot": m["overshoot_pct"],
                "ts": m["settling_time"],
                "iae": m["iae"],
                "ise": m["ise"],
            })
    print("Summary of runs:")
    for row in summary:
        print(row)

if __name__ == "__main__":
    main()
