from __future__ import annotations

from .data_contract import ModelData, Scales, SolverConfig, Solution
from .model_builder import build_model
from .solver import solve_model
from .extract import extract_solution


def run_optimization(
    data: ModelData,
    scales: Scales = Scales(),
    cfg: SolverConfig = SolverConfig(),
    symmetry_breaking: bool = True,
    ensure_e1_breakpoint: bool = True,
    include_per_pump: bool = True,
) -> Solution:
    model, vars_, meta = build_model(
        data=data,
        scales=scales,
        symmetry_breaking=symmetry_breaking,
        ensure_e1_breakpoint=ensure_e1_breakpoint,
    )
    solver, status = solve_model(model, cfg)
    return extract_solution(
        solver=solver,
        status=status,
        data=data,
        scales=scales,
        v=vars_,
        include_per_pump=include_per_pump,
        meta=meta,
    )
