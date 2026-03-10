import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


# Helpers

def _require_cols(df, cols, name="df"):
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns in {name}: {missing}")


def load_results(hourly_csv="results_optimization_hourly.csv", pumps_csv="results_pumps.csv"):
    hourly = pd.read_csv(hourly_csv)
    pumps = pd.read_csv(pumps_csv)
    return hourly, pumps


def _pivot_pumps(pumps_df, value_col):
    """
    Convert long-form pumps_df (hour, pump, value) -> matrix [pump x hour]
    """
    _require_cols(pumps_df, ["hour", "pump", value_col], name="pumps_df")
    mat = pumps_df.pivot(index="pump", columns="hour", values=value_col).sort_index()
    return mat


# Chart 1: Pond volume with bounds

def plot_pond_volume(hourly, Vmin=None, Vmax=None):
    _require_cols(hourly, ["hour", "V_m3"], name="hourly")
    x = hourly["hour"].to_numpy()
    y = hourly["V_m3"].to_numpy()

    plt.figure()
    plt.plot(x, y)
    if Vmin is not None:
        plt.axhline(Vmin, linestyle="--")
    if Vmax is not None:
        plt.axhline(Vmax, linestyle="--")
    plt.xlabel("Hour")
    plt.ylabel("Pond volume (m³)")
    plt.title("Pond volume trajectory")
    plt.tight_layout()


# Chart 2: Water balance bars + volume line

def plot_water_balance(hourly):
    _require_cols(hourly, ["hour", "Vpump_m3", "Vc_m3", "V_m3"], name="hourly")
    x = hourly["hour"].to_numpy()
    vp = hourly["Vpump_m3"].to_numpy()
    vc = hourly["Vc_m3"].to_numpy()
    V = hourly["V_m3"].to_numpy()

    plt.figure()
    plt.bar(x, vp, label="Pumped volume (m³)")
    plt.bar(x, vc, label="V_constant (m³)", bottom=vp)  # will subtract if vc is negative
    plt.plot(x, V, linewidth=2, label="Pond volume (m³)")
    plt.xlabel("Hour")
    plt.title("Hourly water balance and pond volume")
    plt.legend()
    plt.tight_layout()


# Chart 3: Pumps on (system-level)

def plot_pumps_on(hourly):
    _require_cols(hourly, ["hour", "n_on"], name="hourly")
    x = hourly["hour"].to_numpy()
    y = hourly["n_on"].to_numpy()

    plt.figure()
    plt.step(x, y, where="mid")
    plt.xlabel("Hour")
    plt.ylabel("Number of pumps ON")
    plt.title("Pump commitment (count ON)")
    plt.tight_layout()


# Chart 4: Heatmap of per-pump ON/OFF

def plot_per_pump_series(pumps_df, value_col, title, y_label):
    # expects columns: hour, pump, value_col
    pump_ids = sorted(pumps_df["pump"].unique())
    n = len(pump_ids)

    fig, axes = plt.subplots(n, 1, sharex=True)
    if n == 1:
        axes = [axes]

    for ax, pid in zip(axes, pump_ids):
        g = pumps_df[pumps_df["pump"] == pid].sort_values("hour")
        ax.plot(g["hour"], g[value_col])
        ax.set_ylabel(f"P{pid}")

    axes[-1].set_xlabel("Hour")
    fig.suptitle(title)
    fig.tight_layout()


def plot_per_pump_energy_lines(pumps_df):
    plot_per_pump_series(
        pumps_df=pumps_df,
        value_col="e_pump_kwh",
        title="Per-pump energy (kWh)",
        y_label="kWh"
    )


def plot_per_pump_flow_lines(pumps_df):
    plot_per_pump_series(
        pumps_df=pumps_df,
        value_col="v_pump_m3",
        title="Per-pump pumped volume (m³)",
        y_label="m³"
    )



# Chart 7: Energy split (PV used, export, grid) + PV availability

def plot_energy_split(hourly):
    _require_cols(hourly, ["hour", "pv_total_kwh", "e_pv_kwh", "export_kwh", "e_g_kwh"], name="hourly")
    x = hourly["hour"].to_numpy()
    pv_total = hourly["pv_total_kwh"].to_numpy()
    e_pv = hourly["e_pv_kwh"].to_numpy()
    export = hourly["export_kwh"].to_numpy()
    e_g = hourly["e_g_kwh"].to_numpy()

    plt.figure()
    # stacked area: PV used + export + grid (not strictly parts of same total, but very interpretable)
    plt.stackplot(x, e_pv, export, e_g, labels=["PV to pumps", "PV export", "Grid to pumps"])
    plt.plot(x, pv_total, linewidth=2, label="PV available (kWh)")
    plt.xlabel("Hour")
    plt.ylabel("Energy (kWh)")
    plt.title("Energy allocation (PV vs export vs grid)")
    plt.legend(loc="upper right")
    plt.tight_layout()


# Chart 8: Hourly cost breakdown

def plot_hourly_cost_breakdown(hourly):
    _require_cols(
        hourly,
        ["hour", "e_pv_kwh", "e_g_kwh", "export_kwh", "grid_price", "sell_price", "ppa_price"],
        name="hourly",
    )
    x = hourly["hour"].to_numpy()

    pv_cost = hourly["e_pv_kwh"].to_numpy() * hourly["ppa_price"].to_numpy()
    grid_cost = hourly["e_g_kwh"].to_numpy() * hourly["grid_price"].to_numpy()
    export_rev = hourly["export_kwh"].to_numpy() * hourly["sell_price"].to_numpy()
    total = pv_cost + grid_cost - export_rev

    plt.figure()
    plt.bar(x, pv_cost, label="PV cost (PPA)")
    plt.bar(x, grid_cost, bottom=pv_cost, label="Grid cost")
    # show export revenue as negative bar (so "down" reduces total)
    plt.bar(x, -export_rev, label="Export revenue (negative)")
    plt.plot(x, total, linewidth=2, label="Total hourly cost")
    plt.xlabel("Hour")
    plt.ylabel("Currency")
    plt.title("Hourly objective components")
    plt.legend()
    plt.tight_layout()


# Chart 9: Pump curve operating points (scatter) + breakpoints

def plot_operating_points_vs_curve(pumps, E_bp_kwh, Q_bp_m3, per_pump=False):
    _require_cols(pumps, ["e_pump_kwh", "v_pump_m3", "pump"], name="pumps")

    plt.figure()
    if per_pump:
        # one scatter per pump (can get busy if N large)
        for pid, grp in pumps.groupby("pump"):
            plt.scatter(grp["e_pump_kwh"], grp["v_pump_m3"], s=10, label=f"pump {pid}")
        plt.legend()
    else:
        plt.scatter(pumps["e_pump_kwh"], pumps["v_pump_m3"], s=10)

    plt.plot(E_bp_kwh, Q_bp_m3, linewidth=2, label="PWL breakpoints")
    plt.xlabel("Per-pump energy (kWh)")
    plt.ylabel("Per-pump pumped volume (m³)")
    plt.title("Pump curve operating points")
    plt.legend()
    plt.tight_layout()


# One-call convenience: generate the “core” set of charts

def plot_all(hourly_csv="results_optimization_hourly.csv", pumps_csv="results_pumps.csv",
             Vmin=None, Vmax=None, E_bp_kwh=None, Q_bp_m3=None):
    hourly, pumps = load_results(hourly_csv, pumps_csv)

    plot_pond_volume(hourly, Vmin=Vmin, Vmax=Vmax)
    plot_water_balance(hourly)
    plot_pumps_on(hourly)
    plot_energy_split(hourly)
    plot_hourly_cost_breakdown(hourly)

    plot_per_pump_energy_lines(pumps)
    plot_per_pump_flow_lines(pumps)

    # if E_bp_kwh is not None and Q_bp_m3 is not None:
    # plot_operating_points_vs_curve(pumps, E_bp_kwh, Q_bp_m3, per_pump=False)

    plt.show()


if __name__ == "__main__":
    # Fill these for bounds and curve overlay:
    Vmin = 10000.0
    Vmax = 100000.0
    E_bp = [97.86, 100.0, 110.0, 120.0, 130.0, 140.0, 150.0, 160.3]
    Q_bp = [87.299, 124.0, 295.5, 467.0, 638.5, 810.0, 981.5, 1158.145]

    plot_all(Vmin=Vmin, Vmax=Vmax, E_bp_kwh=E_bp, Q_bp_m3=Q_bp)
