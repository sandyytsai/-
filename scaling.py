from __future__ import annotations

from ortools.sat.python import cp_model

from .data_contract import ModelData, Scales, Solution
from .scaling import UnitScaler
from .variables import ModelVars


def extract_solution(
    solver: cp_model.CpSolver,
    status: int,
    data: ModelData,
    scales: Scales,
    v: ModelVars,
    include_per_pump: bool = True,
    meta: dict | None = None,
) -> Solution:
    sc = UnitScaler(scales)

    status_map = {
        cp_model.OPTIMAL: "OPTIMAL",
        cp_model.FEASIBLE: "FEASIBLE",
        cp_model.INFEASIBLE: "INFEASIBLE",
        cp_model.MODEL_INVALID: "MODEL_INVALID",
        cp_model.UNKNOWN: "UNKNOWN",
    }
    status_str = status_map.get(status, "UNKNOWN")

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return Solution(status=status_str)

    T, N = data.T, data.N

    e_pv = [sc.Efloat(solver.Value(v.e_pv[i])) for i in range(T)]
    e_g = [sc.Efloat(solver.Value(v.e_g[i])) for i in range(T)]
    e_total = [sc.Efloat(solver.Value(v.e_total[i])) for i in range(T)]
    e_export = [sc.Efloat(solver.Value(v.e_export[i])) for i in range(T)]
    V_series = [sc.Vfloat(solver.Value(v.V[i])) for i in range(T)]
    Vpump_total = [sc.Vfloat(solver.Value(v.v_pump_total[i])) for i in range(T)]
    n_on = [sum(int(solver.Value(v.y[i][j])) for j in range(N)) for i in range(T)]

    objective_currency = solver.ObjectiveValue() / (scales.COST_SCALE * scales.E_SCALE)

    sol = Solution(
        status=status_str,
        objective_currency=objective_currency,
        e_pv_kwh=e_pv,
        e_g_kwh=e_g,
        e_total_kwh=e_total,
        export_kwh=e_export,
        V_m3=V_series,
        Vpump_m3=Vpump_total,
        n_on=n_on,
        solver_stats={
            "objective_scaled": solver.ObjectiveValue(),
            "wall_time_s": solver.WallTime(),
            "num_conflicts": solver.NumConflicts(),
            "num_branches": solver.NumBranches(),
        }
    )

    if meta is not None and sol.solver_stats is not None:
        sol.solver_stats["meta"] = meta

    if include_per_pump:
        y_on = [[int(solver.Value(v.y[i][j])) for j in range(N)] for i in range(T)]
        e_pump = [[sc.Efloat(solver.Value(v.e_pump[i][j])) for j in range(N)] for i in range(T)]
        v_pump = [[sc.Vfloat(solver.Value(v.v_pump[i][j])) for j in range(N)] for i in range(T)]
        sol.y_on = y_on
        sol.e_pump_kwh = e_pump
        sol.v_pump_m3 = v_pump

    return sol
