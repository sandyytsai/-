from __future__ import annotations

from ortools.sat.python import cp_model

from ..data_contract import ModelData
from ..scaling import UnitScaler
from ..variables import ModelVars


def add_objective(
    m: cp_model.CpModel,
    data: ModelData,
    sc: UnitScaler,
    v: ModelVars,
) -> None:
    T = data.T
    ppa_int = sc.Cint(data.ppa_price)
    grid_int = [sc.Cint(x) for x in data.grid_price]
    sell_int = [sc.Cint(x) for x in data.sell_price]

    terms = []
    for i in range(T):
        terms.append(ppa_int * v.e_pv[i])
        terms.append(grid_int[i] * v.e_g[i])
        terms.append(-sell_int[i] * v.e_export[i])

    m.Minimize(sum(terms))
