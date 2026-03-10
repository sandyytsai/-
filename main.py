import pandas as pd

from solver import ModelData, run_optimization, Scales, SolverConfig
from solver.diagnosis import diagnose_infeasibility

EXCEL_PATH = "project/Test Data.xlsx"   
SHEET = "Sheet3"


def load_test_data(T=288):
    df = pd.read_excel(EXCEL_PATH, sheet_name=SHEET)

    # Use first T hours
    df = df.iloc[:T].copy()

    # Time series inputs (length T)
    pv_total_kwh = df["energy PV output"].astype(float).tolist()
    grid_price = df["price grid"].astype(float).tolist()
    sell_price = df["selling price"].astype(float).tolist()
    ppa_price = float(df["price PPA"].iloc[0])

    # Water demand in m3/h
    demand_m3 = df["water demand"].astype(float).tolist()

    # Precipitation and evaporation in m3/h.
    # If they are in different units (e.g., mm), convert BEFORE building Vc_m3.
    rain_m3 = df["precipitation"].astype(float).tolist()
    evap_m3 = df["evaporation"].astype(float).tolist()

    # Vc = rain - demand - evaporation
    Vc_m3 = [r - d - e for r, d, e in zip(rain_m3, demand_m3, evap_m3)]

    return pv_total_kwh, grid_price, sell_price, ppa_price, Vc_m3


def main():
    # Horizon
    T = 288

    # Load time series from Excel
  
    pv_total_kwh, grid_price, sell_price, ppa_price, Vc_m3 = load_test_data(T=T)

  
    # System & pond parameters
  
    N = 6
    Nmax_on = 6

    E1_kwh = 97.86
    Emax_kwh_per_pump = 160.3
    E1_kwh = E1_kwh / 4  # 15-min timestep
    Emax_kwh_per_pump = Emax_kwh_per_pump / 4

    V0_m3 = 50000.0
    Vmin_m3 = 10000.0
    Vmax_m3 = 100000.0

  
    # Pump curve breakpoints (per pump, per hour)
    # Power [kW] == Energy [kWh] for 1-hour timestep
  
    E_bp_kwh = [97.86, 100.0, 110.0, 120.0, 130.0, 140.0, 150.0, 160.3]
    Q_bp_m3  = [87.299, 124.0, 295.5, 467.0, 638.5, 810.0, 981.5, 1158.145]
    E_bp_kwh = [e/4 for e in E_bp_kwh]
    Q_bp_m3 = [q/4 for q in Q_bp_m3]
  

    data = ModelData(
        T=T,
        N=N,
        Nmax_on=Nmax_on,
        E1_kwh=E1_kwh,
        Emax_kwh_per_pump=Emax_kwh_per_pump,
        E_bp_kwh=E_bp_kwh,
        Q_bp_m3=Q_bp_m3,
        V0_m3=V0_m3,
        Vmin_m3=Vmin_m3,
        Vmax_m3=Vmax_m3,
        Vc_m3=Vc_m3,
        pv_total_kwh=pv_total_kwh,
        grid_price=grid_price,
        sell_price=sell_price,
        ppa_price=ppa_price,
    )

  
    # Scaling & solver configuration
  
    # CP-SAT is integer-only. With our magnitudes (thousands m3/h), a coarser
    # volume scale can speed things up. Start with V_SCALE=1 (m3 as integer).
    scales = Scales(
        E_SCALE=1000,     # kWh -> Wh
        V_SCALE=1000,        # m3 -> mm3 (integer). If you need decimals in Q, raise to 100 or 1000.
        COST_SCALE=1000   # currency -> milli-currency
    )

    cfg = SolverConfig(
        time_limit_s=90.0,
        num_workers=8,
        log_search_progress=False
    )

  
    # Run optimization
  
    sol = run_optimization(
        data=data,
        scales=scales,
        cfg=cfg,
        symmetry_breaking=True,
        ensure_e1_breakpoint=True,
        include_per_pump=True,  # set True for per-pump schedules
    )

    print("Status:", sol.status)

    if sol.status in ("INFEASIBLE", "UNKNOWN"):
        print(f"{sol.status}: likely broken restrictions:")
        for msg in diagnose_infeasibility(data):
            print("-", msg)
        return

    if sol.objective_currency is None:
        return

    print("Objective (currency):", sol.objective_currency)
    print("First 2h - pumps on:", sol.n_on[:8])
    print("First 2h - total pump energy (kWh):", sol.e_total_kwh[:8])
    print("First 2h - grid energy (kWh):", sol.e_g_kwh[:8])
    print("First 2h - PV energy (kWh):", sol.e_pv_kwh[:8])
    print("First 2h - exported energy (kWh):", sol.export_kwh[:8])    
    print("First 2h - pond volume (m3):", sol.V_m3[:8])
    
    # Hourly objective contribution: PV cost + grid cost - export revenue
    hourly_cost = [
        sol.e_pv_kwh[i] * ppa_price
        + sol.e_g_kwh[i] * grid_price[i]
        - sol.export_kwh[i] * sell_price[i]
        for i in range(T)
    ]

    print("First 2h - total cost (currency):", hourly_cost[:8])

    results_df = pd.DataFrame({
        "hour": list(range(T)),
        "pv_total_kwh": pv_total_kwh,
        "e_pv_kwh": sol.e_pv_kwh,
        "e_g_kwh": sol.e_g_kwh,
        "e_total_kwh": sol.e_total_kwh,
        "export_kwh": sol.export_kwh,
        "grid_price": grid_price,
        "sell_price": sell_price,
        "ppa_price": [ppa_price] * T,
        "hourly_cost": hourly_cost,
        "Vc_m3": Vc_m3,
        "V_m3": sol.V_m3,
        "Vpump_m3": sol.Vpump_m3,
        "n_on": sol.n_on,
    })

    out_path = "results_optimization_15m.csv"
    results_df.to_csv(out_path, index=False)

    # Only if include_per_pump=True
    pump_rows = []
    for i in range(T):
        for j in range(N):
            pump_rows.append({
                "hour": i,
                "pump": j,
                "on": sol.y_on[i][j],
                "e_pump_kwh": sol.e_pump_kwh[i][j],
                "v_pump_m3": sol.v_pump_m3[i][j],
            })

    pumps_df = pd.DataFrame(pump_rows)
    pumps_df.to_csv("results_pumps_15m.csv", index=False)


if __name__ == "__main__":
    main()





