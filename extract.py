from __future__ import annotations

from ortools.sat.python import cp_model

from ..data_contract import ModelData
from ..scaling import UnitScaler
from ..variables import ModelVars


def add_storage_balance_constraints(
    m: cp_model.CpModel,
    data: ModelData,
    sc: UnitScaler,
    v: ModelVars,
) -> None:
    T = data.T
    V0 = sc.Vint(data.V0_m3)
    vc = [sc.Vint(x) for x in data.Vc_m3]

    for i in range(T):
        if i == 0:
            m.Add(v.V[i] == V0 + v.v_pump_total[i] + vc[i])
        else:
            m.Add(v.V[i] == v.V[i - 1] + v.v_pump_total[i] + vc[i])
