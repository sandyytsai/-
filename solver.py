from __future__ import annotations

from typing import Tuple, Dict, Any, List

from ortools.sat.python import cp_model

from .data_contract import ModelData, Scales
from .scaling import UnitScaler
from .validation import validate_data, maybe_add_e1_breakpoint
from .variables import create_variables, ModelVars

from .constraints.energy import add_energy_balance_constraints
from .constraints.commitment import add_pump_commitment_constraints
from .constraints.pump_curve_pwl import add_pwl_pump_curve_constraints
from .constraints.storage import add_storage_balance_constraints
from .constraints.objective import add_objective


def build_model(
    data: ModelData,
    scales: Scales,
    symmetry_breaking: bool = True,
    ensure_e1_breakpoint: bool = True,
) -> Tuple[cp_model.CpModel, ModelVars, Dict[str, Any]]:
    validate_data(data)
    sc = UnitScaler(scales)

    E_bp_kwh = data.E_bp_kwh
    Q_bp_m3 = data.Q_bp_m3
    if ensure_e1_breakpoint:
        E_bp_kwh, Q_bp_m3 = maybe_add_e1_breakpoint(E_bp_kwh, Q_bp_m3, data.E1_kwh, Q_at_E1_m3=0.0)

    # Coverage sanity (recommended)
    if data.E1_kwh < E_bp_kwh[0] or data.Emax_kwh_per_pump > E_bp_kwh[-1]:
        raise ValueError(
            "Pump curve breakpoints do not cover [E1, Emax_per_pump]. "
            f"Need E_bp[0] <= E1 and E_bp[-1] >= Emax_per_pump. "
            f"Got E_bp[0]={E_bp_kwh[0]}, E_bp[-1]={E_bp_kwh[-1]}, "
            f"E1={data.E1_kwh}, Emax={data.Emax_kwh_per_pump}"
        )

    E_bp_int: List[int] = [sc.Eint(x) for x in E_bp_kwh]
    Q_bp_int: List[int] = [sc.Vint(x) for x in Q_bp_m3]

    m = cp_model.CpModel()
    v = create_variables(m, data, sc, E_bp_int, Q_bp_int)

    add_energy_balance_constraints(m, data, sc, v)
    add_pump_commitment_constraints(m, data, sc, v, symmetry_breaking=symmetry_breaking)
    add_pwl_pump_curve_constraints(m, data, sc, v, E_bp_int, Q_bp_int)
    add_storage_balance_constraints(m, data, sc, v)
    add_objective(m, data, sc, v)

    meta: Dict[str, Any] = {
        "E_bp_kwh_used": E_bp_kwh,
        "Q_bp_m3_used": Q_bp_m3,
        "E_bp_int_used": E_bp_int,
        "Q_bp_int_used": Q_bp_int,
        "scales": scales,
    }
    return m, v, meta
