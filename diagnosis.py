from __future__ import annotations

from typing import List

from ortools.sat.python import cp_model

from ..data_contract import ModelData
from ..scaling import UnitScaler
from ..variables import ModelVars


def add_pwl_pump_curve_constraints(
    m: cp_model.CpModel,
    data: ModelData,
    sc: UnitScaler,
    v: ModelVars,
    E_bp_int: List[int],
    Q_bp_int: List[int],
) -> None:
    T, N = data.T, data.N
    K = len(E_bp_int)
    S = K - 1
    ES = sc.s.E_SCALE

    Emax = sc.Eint(data.Emax_kwh_per_pump)
    v_pump_max = max(Q_bp_int)

    for i in range(T):
        for j in range(N):
            m.Add(sum(v.z[i][j][k] for k in range(S)) == v.y[i][j])

            for k in range(S):
                m.Add(v.lam[i][j][k] <= v.z[i][j][k] * ES)

            lhs_e = m.NewIntVar(0, Emax * ES, f"lhs_e[{i},{j}]")
            m.Add(lhs_e == v.e_pump[i][j] * ES)

            rhs_e_terms = []
            for k in range(S):
                rhs_e_terms.append(E_bp_int[k] * ES * v.z[i][j][k])
                rhs_e_terms.append((E_bp_int[k + 1] - E_bp_int[k]) * v.lam[i][j][k])
            m.Add(lhs_e == sum(rhs_e_terms))

            lhs_v = m.NewIntVar(0, v_pump_max * ES, f"lhs_v[{i},{j}]")
            m.Add(lhs_v == v.v_pump[i][j] * ES)

            rhs_v_terms = []
            for k in range(S):
                rhs_v_terms.append(Q_bp_int[k] * ES * v.z[i][j][k])
                rhs_v_terms.append((Q_bp_int[k + 1] - Q_bp_int[k]) * v.lam[i][j][k])
            m.Add(lhs_v == sum(rhs_v_terms))

        m.Add(v.v_pump_total[i] == sum(v.v_pump[i][j] for j in range(N)))
