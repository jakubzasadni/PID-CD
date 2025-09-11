# src/run_scenario.py
# Runs a step response scenario, saves CSV, PNG, and simple HTML report.
# Exits with code 0 if gates pass, otherwise 1.

import os, csv, json, sys
from pathlib import Path
import matplotlib.pyplot as plt

from src.model import FirstOrderTank
from src.pid import PID
from src.metrics import compute_metrics


def getenv_float(key, default):
    try:
        return float(os.getenv(key, default))
    except Exception:
        return default


def main():
    # Parameters from environment
    K = getenv_float("PLANT_K", 1.0)
    TAU = getenv_float("PLANT_TAU", 30.0)
    DT = getenv_float("SIM_DT", 0.05)
    T_SIM = getenv_float("SIM_TIME", 60.0)

    KP = getenv_float("PID_KP", 1.0)
    TI = getenv_float("PID_TI", 30.0)
    TD = getenv_float("PID_TD", 0.0)
    N = getenv_float("PID_N", 10.0)
    UMIN = getenv_float("U_MIN", 0.0)
    UMAX = getenv_float("U_MAX", 1.0)
    KAW = getenv_float("PID_KAW", 1.0)

    R_FINAL = getenv_float("STEP_FINAL", 1.0)
    SETTLE_BAND = getenv_float("SETTLE_BAND", 0.02)

    # Quality gates (progi oceny)
    GATE_OVERSHOOT = getenv_float("GATE_MAX_OVERSHOOT_PCT", 15.0)
    GATE_TS_MULT_TAU = getenv_float("GATE_MAX_TS_MULT_TAU", 5.0)
    GATE_IAE_MAX = getenv_float("GATE_MAX_IAE", 50.0)

    out_dir = Path(os.getenv("OUT_DIR", "/out"))
    out_dir.mkdir(parents=True, exist_ok=True)

    # Init plant and controller
    plant = FirstOrderTank(K=K, tau=TAU, dt=DT)
    pid = PID(kp=KP, ti=TI, td=TD, dt=DT, n=N, umin=UMIN, umax=UMAX, kaw=KAW)
    plant.reset(0.0)
    pid.reset()

    t, r, y, u, e = [], [], [], [], []
    steps = int(T_SIM / DT)

    for k in range(steps + 1):
        time = k * DT
        ref = R_FINAL
        ctrl = pid.update(ref, plant.y)
        y_next = plant.step(ctrl)

        t.append(time)
        r.append(ref)
        y.append(y_next)
        u.append(ctrl)
        e.append(ref - y_next)

    # Metrics
    m = compute_metrics(t, r, y, e, settle_band=SETTLE_BAND)

    # Save CSV
    csv_path = out_dir / "results.csv"
    with csv_path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["t", "r", "y", "u", "e"])
        for i in range(len(t)):
            w.writerow([t[i], r[i], y[i], u[i], e[i]])

    # Plot
    plt.figure()
    plt.plot(t, r, label="r")
    plt.plot(t, y, label="y")
    plt.plot(t, u, label="u")
    plt.legend()
    plt.xlabel("t [s]")
    plt.ylabel("value")
    plt.title("Step response")
    plt.savefig(out_dir / "plot.png", dpi=120, bbox_inches="tight")
    plt.close()

    # JSON report
    report = {
        "plant": {"K": K, "tau": TAU},
        "pid": {"kp": KP, "ti": TI, "td": TD, "n": N, "umin": UMIN, "umax": UMAX, "kaw": KAW},
        "sim": {"dt": DT, "T": T_SIM, "r_final": R_FINAL},
        "metrics": {
            "rise_time": m.rise_time,
            "settling_time": m.settling_time,
            "overshoot_pct": m.overshoot_pct,
            "iae": m.iae,
            "ise": m.ise,
        },
    }
    (out_dir / "report.json").write_text(json.dumps(report, indent=2))

    # HTML report
    html = f"""
    <html><body>
    <h2>Validation report</h2>
    <pre>{json.dumps(report, indent=2)}</pre>
    <img src="plot.png" width="640"/>
    </body></html>
    """
    (out_dir / "report.html").write_text(html)

    # === Quality gates check ===
    fail = False
    if m.overshoot_pct > GATE_OVERSHOOT:
        print(f"FAIL: overshoot {m.overshoot_pct:.2f} > {GATE_OVERSHOOT}")
        fail = True
    if m.settling_time > GATE_TS_MULT_TAU * TAU:
        print(f"FAIL: settling_time {m.settling_time:.2f} > {GATE_TS_MULT_TAU * TAU}")
        fail = True
    if m.iae > GATE_IAE_MAX:
        print(f"FAIL: IAE {m.iae:.2f} > {GATE_IAE_MAX}")
        fail = True

    if fail:
        print("Quality gates FAILED ❌")
        sys.exit(1)
    else:
        print("Quality gates PASSED ✅")
        sys.exit(0)


if __name__ == "__main__":
    main()
