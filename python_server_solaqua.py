from __future__ import annotations

from dataclasses import dataclass
from typing import List

from ortools.sat.python import cp_model

from .data_contract import ModelData
from .scaling import UnitScaler


@dataclass
class ModelVars:
    # System-level energy allocation
    e_pv: List[cp_model.IntVar]
    e_g: List[cp_model.IntVar]
    e_total: List[cp_model.IntVar]
    e_export: List[cp_model.IntVar]

    # Storage and pumping totals
    V: List[cp_model.IntVar]
    v_pump_total: List[cp_model.IntVar]

    # Per-pump
    y: List[List[cp_model.BoolVar]]
    e_pump: List[List[cp_model.IntVar]]
    v_pump: List[List[cp_model.IntVar]]

    # PWL auxiliaries
    z: List[List[List[cp_model.BoolVar]]]
    lam: List[List[List[cp_model.IntVar]]]


def create_variables(
    m: cp_model.CpModel,
    data: ModelData,
    sc: UnitScaler,
    E_bp_int: List[int],
    Q_bp_int: List[int],
) -> ModelVars:
    T, N = data.T, data.N
    pv_total = [sc.Eint(x) for x in data.pv_total_kwh]

    Emax = sc.Eint(data.Emax_kwh_per_pump)
    Emax_total = N * Emax

    # System-level energy vars
    e_pv = [m.NewIntVar(0, pv_total[i], f"e_pv[{i}]") for i in range(T)]
    e_g = [m.NewIntVar(0, Emax_total, f"e_g[{i}]") for i in range(T)]
    e_total = [m.NewIntVar(0, Emax_total, f"e_total[{i}]") for i in range(T)]
    e_export = [m.NewIntVar(0, pv_total[i], f"e_export[{i}]") for i in range(T)]

    # Storage vars
    Vmin = sc.Vint(data.Vmin_m3)
    Vmax = sc.Vint(data.Vmax_m3)
    V = [m.NewIntVar(Vmin, Vmax, f"V[{i}]") for i in range(T)]

    # Per-pump vars
    y = [[m.NewBoolVar(f"y[{i},{j}]") for j in range(N)] for i in range(T)]
    e_pump = [[m.NewIntVar(0, Emax, f"e_pump[{i},{j}]") for j in range(N)] for i in range(T)]

    v_pump_max = max(Q_bp_int)
    v_pump = [[m.NewIntVar(0, v_pump_max, f"v_pump[{i},{j}]") for j in range(N)] for i in range(T)]
    v_pump_total = [m.NewIntVar(0, N * v_pump_max, f"v_pump_total[{i}]") for i in range(T)]

    # PWL auxiliaries
    K = len(E_bp_int)
    S = K - 1
    z = [[[m.NewBoolVar(f"z[{i},{j},{k}]") for k in range(S)] for j in range(N)] for i in range(T)]
    lam = [[[m.NewIntVar(0, sc.s.E_SCALE, f"lam[{i},{j},{k}]") for k in range(S)] for j in range(N)] for i in range(T)]

    return ModelVars(
        e_pv=e_pv,
        e_g=e_g,
        e_total=e_total,
        e_export=e_export,
        V=V,
        v_pump_total=v_pump_total,
        y=y,
        e_pump=e_pump,
        v_pump=v_pump,
        z=z,
        lam=lam,
    )
