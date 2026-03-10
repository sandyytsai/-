from __future__ import annotations

from ortools.sat.python import cp_model

from ..data_contract import ModelData
from ..scaling import UnitScaler
from ..variables import ModelVars


def add_energy_balance_constraints(
    m: cp_model.CpModel,
    data: ModelData,
    sc: UnitScaler,
    v: ModelVars,
) -> None:
    T, N = data.T, data.N
    pv_total = [sc.Eint(x) for x in data.pv_total_kwh]

    for i in range(T):
        m.Add(v.e_total[i] == sum(v.e_pump[i][j] for j in range(N)))
        m.Add(v.e_total[i] == v.e_pv[i] + v.e_g[i])
        m.Add(v.e_export[i] == pv_total[i] - v.e_pv[i])
