import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from ortools.sat.python import cp_model

from solver import ModelData, Scales
from solver.model_builder import build_model

EXCEL_PATH = "project/Test Data.xlsx"
SHEET = "Sheet1"


def load_test_data(T=72):
    import pandas as pd
    df = pd.read_excel(EXCEL_PATH, sheet_name=SHEET).iloc[:T].copy()

    pv_total_kwh = df["energy PV output"].astype(float).tolist()
    grid_price = df["price grid"].astype(float).tolist()
    sell_price = df["selling price"].astype(float).tolist()
    ppa_price = float(df["price PPA"].iloc[0])

    demand_m3 = df["water demand"].astype(float).tolist()
    rain_m3 = df["precipitation"].astype(float).tolist()
    evap_m3 = df["evaporation"].astype(float).tolist()
    Vc_m3 = [r - d - e for r, d, e in zip(rain_m3, demand_m3, evap_m3)]
    return pv_total_kwh, grid_price, sell_price, ppa_price, Vc_m3


def make_model_data(T=72):
    pv_total_kwh, grid_price, sell_price, ppa_price, Vc_m3 = load_test_data(T=T)

    return ModelData(
        T=T,
        N=6,
        Nmax_on=6,
        E1_kwh=97.86,
        Emax_kwh_per_pump=160.3,
        E_bp_kwh=[97.86, 100.0, 110.0, 120.0, 130.0, 140.0, 150.0, 160.3],
        Q_bp_m3=[87.299, 124.0, 295.5, 467.0, 638.5, 810.0, 981.5, 1158.145],
        V0_m3=40000.0,
        Vmin_m3=10000.0,
        Vmax_m3=100000.0,
        Vc_m3=Vc_m3,
        pv_total_kwh=pv_total_kwh,
        grid_price=grid_price,
        sell_price=sell_price,
        ppa_price=ppa_price,
    )


class IncumbentTrace(cp_model.CpSolverSolutionCallback):
    def __init__(self):
        super().__init__()
        self._t0 = time.time()
        self.t_s = []
        self.obj_scaled = []

    def OnSolutionCallback(self):
        self.t_s.append(time.time() - self._t0)
        self.obj_scaled.append(self.ObjectiveValue())


def run_one_trace(model, scales, time_limit_s, seed, num_workers=8):
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = float(time_limit_s)
    solver.parameters.num_search_workers = int(num_workers)
    solver.parameters.random_seed = int(seed)
    solver.parameters.log_search_progress = False

    cb = IncumbentTrace()
    status = solver.Solve(model, cb)  # <-- compatible with your version

    # Convert to currency
    obj_cur = [v / (scales.COST_SCALE * scales.E_SCALE) for v in cb.obj_scaled]

    return {
        "seed": seed,
        "status": status,
        "t_s": cb.t_s,
        "obj_cur": obj_cur,
        "final_obj": (solver.ObjectiveValue() / (scales.COST_SCALE * scales.E_SCALE))
                    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE) else None
    }


def step_value_at(times, values, tgrid):
    """
    For a step plot ('best so far'), return value at each t in tgrid.
    Assumes times are increasing, values correspond to improvements.
    Uses 'post' convention: value holds until next improvement.
    """
    if len(times) == 0:
        return np.full_like(tgrid, np.nan, dtype=float)

    times = np.asarray(times, dtype=float)
    values = np.asarray(values, dtype=float)

    out = np.empty_like(tgrid, dtype=float)
    j = 0
    current = values[0]
    for i, t in enumerate(tgrid):
        while j < len(times) and times[j] <= t:
            current = values[j]
            j += 1
        out[i] = current
    return out


def main():
    # Settings
    time_limit_s = 60.0
    seeds = [1, 2, 3, 4, 5,6,7,8,9,10]   # increase to 10–20 for nicer statistics
    num_workers = 8

    # Build model ONCE (same instance for all runs)
    data = make_model_data(T=72)
    scales = Scales(E_SCALE=1000, V_SCALE=1, COST_SCALE=1000)

    model, vars_, meta = build_model(
        data=data,
        scales=scales,
        symmetry_breaking=True,
        ensure_e1_breakpoint=True,
    )

    traces = []
    for s in seeds:
        tr = run_one_trace(model, scales, time_limit_s=time_limit_s, seed=s, num_workers=num_workers)
        traces.append(tr)
        print(f"seed={s} final_obj={tr['final_obj']} incumbents={len(tr['t_s'])}")

    # Save all traces (long format) so you can reuse without rerunning
    rows = []
    for tr in traces:
        for t, obj in zip(tr["t_s"], tr["obj_cur"]):
            rows.append({"seed": tr["seed"], "t_s": t, "objective_currency": obj})
    pd.DataFrame(rows).to_csv("incumbent_overlay_traces.csv", index=False)
    print("Saved: incumbent_overlay_traces.csv")

    # --- Plot overlay ---
    plt.figure()
    for tr in traces:
        if len(tr["t_s"]) == 0:
            continue
        plt.step(tr["t_s"], tr["obj_cur"], where="post", alpha=0.6, label=f"seed {tr['seed']}")

    plt.xlabel("Time (s)")
    plt.ylabel("Best objective so far (currency)")
    plt.title("Convergence (multiple runs)")
    plt.legend()
    plt.tight_layout()

    # --- Optional: plot median curve across runs ---
    # Build a common time grid
    tgrid = np.linspace(0, time_limit_s, 200)

    curves = []
    for tr in traces:
        if len(tr["t_s"]) == 0:
            continue
        curves.append(step_value_at(tr["t_s"], tr["obj_cur"], tgrid))

    if len(curves) >= 2:
        curves = np.vstack(curves)
        median = np.nanmedian(curves, axis=0)

        plt.figure()
        for tr in traces:
            if len(tr["t_s"]) == 0:
                continue
            plt.step(tr["t_s"], tr["obj_cur"], where="post", alpha=0.25)

        plt.plot(tgrid, median, linewidth=2, label="Median (step-interpolated)")
        plt.xlabel("Time (s)")
        plt.ylabel("Best objective so far (currency)")
        plt.title("Convergence: runs + median curve")
        plt.legend()
        plt.tight_layout()

    plt.show()


if __name__ == "__main__":
    main()
