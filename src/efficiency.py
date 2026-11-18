cat > src/efficiency.py <<'EOF'
"""
efficiency.py - Phase 5: employee and department (airline) efficiency

Joins BTS on-time data (Phase 3 output) with BTS Schedule P-1(a) employment
(full-time equivalent employees, FTE) by airline and month.
FTEs cover the whole workforce while flights are US domestic only, so airlines
are compared within peer groups (Network / Low-cost / Regional).

Run:  python src/efficiency.py
"""
import glob
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
EMP = ROOT / "data" / "raw" / "employment"

NETWORK = {"AA", "DL", "UA", "AS", "HA"}
LOW_COST = {"WN", "B6", "NK", "F9", "G4", "SY", "MX", "XP"}
GROUP_COLORS = {"Network": "#2a78d6", "Low-cost": "#e8833a", "Regional": "#5ba77f"}


def peer_group(code):
    return "Network" if code in NETWORK else "Low-cost" if code in LOW_COST else "Regional"


def main():
    (OUT / "tableau").mkdir(parents=True, exist_ok=True)
    (OUT / "charts").mkdir(parents=True, exist_ok=True)

    files = sorted(glob.glob(str(EMP / "*.csv")))
    emp = pd.concat((pd.read_csv(f) for f in files), ignore_index=True)
    emp.columns = emp.columns.str.strip().str.upper()
    emp = emp.drop_duplicates(["YEAR", "MONTH", "CARRIER"])
    emp = emp.groupby(["YEAR", "MONTH", "CARRIER"], as_index=False)["EMPFTE"].sum()
    emp.columns = ["year", "month", "carrier", "fte"]

    m = pd.read_csv(OUT / "tableau" / "airline_monthly.csv")
    j = m.merge(emp, on=["year", "month", "carrier"], how="left")
    missing = j[j["fte"].isna()]
    covered = j.dropna(subset=["fte"]).copy()
    covered = covered[covered["fte"] > 0]
    covered["peer_group"] = covered["carrier"].map(peer_group)
    covered["flights_per_fte"] = covered["flights"] / covered["fte"]
    covered.to_csv(OUT / "tableau" / "airline_efficiency_monthly.csv", index=False)

    a = covered.groupby(["carrier", "carrier_name", "peer_group"]).agg(
        months=("period", "nunique"), flights=("flights", "sum"), delayed=("delayed", "sum"),
        cancelled=("cancelled", "sum"), diverted=("diverted", "sum"),
        controllable_min=("controllable_min", "sum"), delay_cost=("delay_cost", "sum"),
        avg_fte=("fte", "mean")).reset_index()
    a["flights_per_fte_month"] = a["flights"] / a["months"] / a["avg_fte"]
    a["on_time_rate"] = 1 - (a["delayed"] + a["cancelled"] + a["diverted"]) / a["flights"]
    a["cancel_rate"] = a["cancelled"] / a["flights"]
    a["controllable_min_per_flight"] = a["controllable_min"] / a["flights"]
    a["delay_cost_per_fte_year"] = a["delay_cost"] / a["months"] * 12 / a["avg_fte"]
    a = a.sort_values(["peer_group", "flights_per_fte_month"], ascending=[True, False])
    a.round(4).to_csv(OUT / "airline_efficiency.csv", index=False)

    print(f"Employment files: {len(files)} | Airline-months matched: {len(covered):,} of {len(j):,}")
    if len(missing):
        gap = missing.groupby("carrier_name")["period"].agg(["count", "min", "max"])
        print("No employment match for:\n" + gap.to_string())

    show = a.copy()
    show["avg_fte"] = show["avg_fte"].map("{:,.0f}".format)
    show["flights_per_fte_month"] = show["flights_per_fte_month"].map("{:.2f}".format)
    show["on_time_rate"] = show["on_time_rate"].map("{:.1%}".format)
    show["cancel_rate"] = show["cancel_rate"].map("{:.1%}".format)
    show["controllable_min_per_flight"] = show["controllable_min_per_flight"].map("{:.1f}".format)
    show["delay_cost_per_fte_year"] = show["delay_cost_per_fte_year"].map("${:,.0f}".format)
    for g, d in show.groupby("peer_group", sort=False):
        print(f"\n{g.upper()} (sorted by flights per employee per month)")
        print(d[["carrier_name", "avg_fte", "flights_per_fte_month", "on_time_rate", "cancel_rate",
                 "controllable_min_per_flight", "delay_cost_per_fte_year"]].to_string(index=False))

    c = a.sort_values(["peer_group", "flights_per_fte_month"])
    fig, ax = plt.subplots(figsize=(9, 0.3 * len(c) + 1.4))
    ax.barh(c["carrier_name"], c["flights_per_fte_month"], color=c["peer_group"].map(GROUP_COLORS))
    for g, col in GROUP_COLORS.items():
        ax.barh([], [], color=col, label=g)
    ax.legend(frameon=False, fontsize=9, loc="lower right")
    ax.set_xlabel("Domestic arriving flights per FTE employee per month")
    ax.set_title("Flights per employee, compared within peer groups", loc="left", fontsize=12)
    for s in ["top", "right"]:
        ax.spines[s].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUT / "charts" / "flights_per_fte.png", dpi=150)
    plt.close(fig)
    print("\nSaved: outputs/tableau/airline_efficiency_monthly.csv, outputs/airline_efficiency.csv, outputs/charts/flights_per_fte.png")


if __name__ == "__main__":
    main()
