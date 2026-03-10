from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Dict, Any


@dataclass(frozen=True)
class Scales:
    # kWh * E_SCALE -> integer energy units (e.g., 1000 => Wh)
    E_SCALE: int = 1000
    # m3 * V_SCALE -> integer volume units (e.g., 1000 => liters)
    V_SCALE: int = 1000
    # currency * COST_SCALE -> integer currency units (e.g., 1000 => milli-currency)
    COST_SCALE: int = 1000


@dataclass(frozen=True)
class SolverConfig:
    time_limit_s: float = 10.0
    num_workers: int = 8
    log_search_progress: bool = False


@dataclass(frozen=True)
class ModelData:
    # Horizon
    T: int

    # Pumps
    N: int
    Nmax_on: int

    # Per-pump operating limits (kWh per hour)
    E1_kwh: float
    Emax_kwh_per_pump: float

    # Pump curve breakpoints (per pump, per hour)
    E_bp_kwh: List[float]
    Q_bp_m3: List[float]

    # Storage (m3)
    V0_m3: float
    Vmin_m3: float
    Vmax_m3: float

    # Exogenous volume driver per hour (m3): Vc = rain - demand - evap (can be negative)
    Vc_m3: List[float]

    # PV and prices
    pv_total_kwh: List[float]      # length T, >=0
    grid_price: List[float]        # currency/kWh, length T
    sell_price: List[float]        # currency/kWh, length T
    ppa_price: float               # currency/kWh (scalar)


@dataclass
class Solution:
    status: str
    objective_currency: Optional[float] = None

    # System-level time series (length T)
    e_pv_kwh: Optional[List[float]] = None
    e_g_kwh: Optional[List[float]] = None
    e_total_kwh: Optional[List[float]] = None
    export_kwh: Optional[List[float]] = None
    V_m3: Optional[List[float]] = None
    Vpump_m3: Optional[List[float]] = None
    n_on: Optional[List[int]] = None

    # Per-pump (optional)
    y_on: Optional[List[List[int]]] = None
    e_pump_kwh: Optional[List[List[float]]] = None
    v_pump_m3: Optional[List[List[float]]] = None

    # Diagnostics
    solver_stats: Optional[Dict[str, Any]] = None
