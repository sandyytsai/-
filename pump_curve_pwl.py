from __future__ import annotations

from ortools.sat.python import cp_model

from ..data_contract import ModelData
from ..scaling import UnitScaler
from ..variables import ModelVars


def add_pump_commitment_constraints(
    m: cp_model.CpModel,
    data: ModelData,
    sc: UnitScaler,
    v: ModelVars,
    symmetry_breaking: bool = True,
) -> None:
    T, N = data.T, data.N
    E1 = sc.Eint(data.E1_kwh)
    Emax = sc.Eint(data.Emax_kwh_per_pump)

    for i in range(T):
        m.Add(sum(v.y[i][j] for j in range(N)) <= data.Nmax_on)

        for j in range(N):
            m.Add(v.e_pump[i][j] <= Emax * v.y[i][j])
            m.Add(v.e_pump[i][j] >= E1 * v.y[i][j])

        if symmetry_breaking and N >= 2:
            for j in range(N - 1):
                m.Add(v.y[i][j] >= v.y[i][j + 1])
            for j in range(N - 1):
                m.Add(v.e_pump[i][j] >= v.e_pump[i][j + 1])
