"""
costs.py - Phase 3: operational cost of delays

Turns delay minutes into dollars with the Airlines for America (A4A) published
direct aircraft operating cost per block minute, then breaks the cost down by
airline, cause (controllable vs not) and month.

Cost assumption
  $100.76 per delay minute = A4A 2024 average direct operating cost per block
  minute for US passenger airlines (crew, fuel, maintenance, ownership, other).
  Some arrival delay is spent at the gate with engines off, so this is an
  upper-bound estimate of the airline's direct cost. Passenger time is not included.

Outputs
  outputs/tableau/airline_monthly.csv
  outputs/cost_by_airline.csv
  outputs/charts/cost_by_airline.png

Run:  python src/costs.py
"""
import sqlite3
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "processed" / "ops.db"
SQL = ROOT / "sql"
OUT = ROOT / "outputs"
COST_PER_MIN = 100.76   # A4A, 2024 direct aircraft operating cost per block minute
BLUE, GREY, INK, INK2, GRID = "#2a78d6", "#c3c2b7", "#0b0b0b", "#52514e", "#e1e0d9"


def money(x):
    return f"${x / 1e9:,.2f}B" if abs(x) >= 1e9 else f"${x / 1e6:,.1f}M"


def main():
    (OUT / "tableau").mkdir(parents=True, exist_ok=True)
    (OUT / "charts").mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB) as con:
        m = pd.read_sql((SQL / "airline_monthly.sql").read_text(), con)

    for c in ["delay", "controllable", "carrier", "late_aircraft", "weather", "nas"]:
        m[f"{c}_cost"] = m[f"{c}_min"] * COST_PER_MIN
    m.to_csv(OUT / "tableau" / "airline_monthly.csv", index=False)

    a = m.groupby(["carrier", "carrier_name"]).agg(
        flights=("flights", "sum"), delay_min=("delay_min", "sum"),
        controllable_min=("controllable_min", "sum"), delay_cost=("delay_cost", "sum"),
        controllable_cost=("controllable_cost", "sum")).reset_index()
    a["cost_per_flight"] = a["delay_cost"] / a["flights"]
    a["controllable_cost_per_flight"] = a["controllable_cost"] / a["flights"]
    a["controllable_share"] = a["controllable_min"] / a["delay_min"]
    a["share_of_total_cost"] = a["delay_cost"] / a["delay_cost"].sum()
    a = a.sort_values("delay_cost", ascending=False)
    a.round(4).to_csv(OUT / "cost_by_airline.csv", index=False)

    total, ctrl = m["delay_cost"].sum(), m["controllable_cost"].sum()
    months = m["period"].nunique()
    yearly = m[m["year"] < m["year"].max()].groupby("year")["delay_cost"].sum()
    by_month = m.groupby("month")["delay_cost"].sum() / m.groupby("month")["period"].nunique()

    print(f"COST OF DELAY at ${COST_PER_MIN}/minute (A4A 2024 direct operating cost, upper bound)")
    print(f"  Total over {months} months:   {money(total)}  ({money(total / months * 12)} a year)")
    print(f"  Controllable by airlines:   {money(ctrl)}  ({ctrl / total:.0%})")
    print(f"  Average cost per flight:    ${total / m['flights'].sum():,.0f}")
    print("  Full years:  " + "  ".join(f"{y}: {money(v)}" for y, v in yearly.items()))
    print(f"  Costliest month on average: {pd.Timestamp(2000, by_month.idxmax(), 1):%B} "
          f"({money(by_month.max())}) vs cheapest {pd.Timestamp(2000, by_month.idxmin(), 1):%B} "
          f"({money(by_month.min())})")

    show = a.copy()
    show["delay_cost"] = show["delay_cost"].map(money)
    show["cost_per_flight"] = show["cost_per_flight"].map(lambda x: f"${x:,.0f}")
    show["controllable_cost_per_flight"] = show["controllable_cost_per_flight"].map(lambda x: f"${x:,.0f}")
    show["controllable_share"] = show["controllable_share"].map(lambda x: f"{x:.0%}")
    show["flights"] = show["flights"].map(lambda x: f"{x:,.0f}")
    print("\nBy airline (highest total cost first)")
    print(show[["carrier_name", "flights", "delay_cost", "cost_per_flight",
                "controllable_cost_per_flight", "controllable_share"]].to_string(index=False))

    # chart: cost per flight, split controllable vs not
    c = a.sort_values("cost_per_flight")
    fig, ax = plt.subplots(figsize=(9, 0.32 * len(c) + 1.4))
    ax.barh(c["carrier_name"], c["controllable_cost_per_flight"], color=BLUE, label="Controllable (carrier + late aircraft)")
    ax.barh(c["carrier_name"], c["cost_per_flight"] - c["controllable_cost_per_flight"],
            left=c["controllable_cost_per_flight"], color=GREY, label="Weather, air traffic, security")
    ax.set_xlabel("Delay cost per scheduled flight ($)", color=INK2)
    ax.set_title("Delay cost per flight by airline", loc="left", fontsize=12, color=INK)
    ax.legend(frameon=False, fontsize=9, loc="lower right")
    for s in ["top", "right"]:
        ax.spines[s].set_visible(False)
    ax.grid(axis="x", color=GRID)
    ax.set_axisbelow(True)
    ax.tick_params(colors=INK2, labelsize=9)
    fig.tight_layout()
    fig.savefig(OUT / "charts" / "cost_by_airline.png", dpi=150)
    plt.close(fig)
    print("\nSaved: outputs/tableau/airline_monthly.csv, outputs/cost_by_airline.csv, outputs/charts/cost_by_airline.png")


if __name__ == "__main__":
    main()
