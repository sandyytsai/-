from __future__ import annotations

from typing import List
from .data_contract import ModelData


def diagnose_infeasibility(data):
    
    reasons: List[str] = []

    T = data.T
    Vmin, Vmax, V0 = data.Vmin_m3, data.Vmax_m3, data.V0_m3

    # 1) Pump curve coverage
    if min(data.E_bp_kwh) > data.E1_kwh or max(data.E_bp_kwh) < data.Emax_kwh_per_pump:
        reasons.append("Pump curve breakpoints do not cover [E1, Emax] per pump.")

    # 2) Max pumping per hour (m3/h)
    Qmax_per_pump = max(data.Q_bp_m3)
    Qmax_total = data.Nmax_on * Qmax_per_pump

    # 3) Lower-bound reachability check (best case: max pumping every hour)
    V = V0
    first_violation_hour = None
    for i in range(T):
        V = V + Qmax_total + data.Vc_m3[i]
        if V < Vmin and first_violation_hour is None:
            first_violation_hour = i

    if first_violation_hour is not None:
        reasons.append(
            f"Even with MAX pumping every hour, pond volume drops below Vmin at hour {first_violation_hour}."
        )

    # 4) Upper-bound reachability check (best case: pumps OFF)
    V = V0
    first_overflow_hour = None
    for i in range(T):
        V = V + data.Vc_m3[i]
        if V > Vmax and first_overflow_hour is None:
            first_overflow_hour = i

    if first_overflow_hour is not None:
        reasons.append(
            f"Even with pumps OFF, pond volume exceeds Vmax at hour {first_overflow_hour}."
        )

    # 5) Fallback
    if not reasons:
        reasons.append(
            "Model reported INFEASIBLE, but simple reachability checks did not find an obvious cause. "
            "Check units (m³ vs L), Vc sign conventions, breakpoint consistency, or rounding from scaling."
        )

    return reasons