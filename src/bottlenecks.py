"""
bottlenecks.py - Phase 4: where and why delays build up

1. Cause mix: which of the 5 causes drive delay minutes, overall and by airline
2. Delay cascade: late aircraft minutes created per minute of the airline's own
   (carrier) delay. A high ratio means one problem spreads through the day.
3. Airport bottlenecks (sql/airport_bottlenecks.sql): Pareto of delay minutes,
   and the busiest airports with the worst on-time rate
4. Seasonality: delay minutes per flight by calendar month

Outputs
  outputs/tableau/airport_bottlenecks.csv
  outputs/cause_mix_by_airline.csv
  outputs/charts/cause_mix.png, outputs/charts/airport_pareto.png

Run:  python src/bottlenecks.py
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
CAUSES = {"carrier_min": "Carrier (crew, maintenance, ops)", "late_aircraft_min": "Late-arriving aircraft",
          "nas_min": "Air traffic / airspace (NAS)", "weather_min": "Extreme weather", "security_min": "Security"}
BUSY_MIN_SHARE = 0.005   # an airport counts as "busy" with at least 0.5% of all flights
BLUE, INK, INK2, GRID = "#2a78d6", "#0b0b0b", "#52514e", "#e1e0d9"


def style(ax):
    for s in ["top", "right"]:
        ax.spines[s].set_visible(False)
    ax.grid(color=GRID)
    ax.set_axisbelow(True)
    ax.tick_params(colors=INK2, labelsize=9)


def main():
    (OUT / "tableau").mkdir(parents=True, exist_ok=True)
    (OUT / "charts").mkdir(parents=True, exist_ok=True)
    m = pd.read_csv(OUT / "tableau" / "airline_monthly.csv")
    with sqlite3.connect(DB) as con:
        ap = pd.read_sql((SQL / "airport_bottlenecks.sql").read_text(), con)

    # 1. cause mix
    total = m[list(CAUSES)].sum()
    mix = (total / total.sum()).rename(index=CAUSES).sort_values(ascending=False)
    by_air = m.groupby("carrier_name")[list(CAUSES)].sum()
    by_air = by_air.div(by_air.sum(axis=1), axis=0).rename(columns=CAUSES)

    # 2. cascade ratio
    g = m.groupby("carrier_name")[["carrier_min", "late_aircraft_min", "flights"]].sum()
    g["cascade_ratio"] = g["late_aircraft_min"] / g["carrier_min"]
    by_air["cascade_ratio"] = g["cascade_ratio"]
    by_air.round(4).to_csv(OUT / "cause_mix_by_airline.csv")

    # 3. airports
    ap["busy"] = ap["flights"] >= ap["flights"].sum() * BUSY_MIN_SHARE
    ap.to_csv(OUT / "tableau" / "airport_bottlenecks.csv", index=False)
    n_half = int((ap["cumulative_share"] < 0.5).sum()) + 1
    busy = ap[ap["busy"]].sort_values("on_time_rate")

    # 4. seasonality
    s = m.groupby("month")[["delay_min", "flights"]].sum()
    s["min_per_flight"] = s["delay_min"] / s["flights"]

    print("1. WHAT CAUSES DELAY (share of all delay minutes)")
    for k, v in mix.items():
        print(f"   {k:<34}{v:6.1%}")
    ctrl = mix["Carrier (crew, maintenance, ops)"] + mix["Late-arriving aircraft"]
    print(f"   -> {ctrl:.0%} is controllable by the airline (carrier + late aircraft)")

    print("\n2. DELAY CASCADE (late-aircraft minutes per carrier-delay minute; higher = problems spread)")
    for k, v in g["cascade_ratio"].sort_values(ascending=False).items():
        print(f"   {k:<34}{v:5.2f}")

    print(f"\n3. AIRPORT BOTTLENECKS ({len(ap)} airports)")
    print(f"   {n_half} airports ({n_half / len(ap):.0%}) account for half of all delay minutes")
    print(f"   Busiest airports (>= {BUSY_MIN_SHARE:.1%} of flights) with the worst on-time rate:")
    print(busy.head(8)[["airport", "airport_name", "flights", "on_time_rate", "delay_min_per_flight"]]
          .assign(flights=lambda d: d.flights.map("{:,.0f}".format),
                  on_time_rate=lambda d: d.on_time_rate.map("{:.1%}".format))
          .to_string(index=False))

    worst, best = s["min_per_flight"].idxmax(), s["min_per_flight"].idxmin()
    print(f"\n4. SEASONALITY: worst month {pd.Timestamp(2000, worst, 1):%B} "
          f"({s.loc[worst, 'min_per_flight']:.1f} delay min per flight), best "
          f"{pd.Timestamp(2000, best, 1):%B} ({s.loc[best, 'min_per_flight']:.1f})")

    # charts
    fig, ax = plt.subplots(figsize=(8, 3.2))
    mm = mix.sort_values()
    ax.barh(mm.index, mm.values * 100, color=BLUE)
    for i, v in enumerate(mm.values):
        ax.text(v * 100 + 0.5, i, f"{v:.0%}", va="center", fontsize=9, color=INK)
    ax.set_xlabel("Share of all delay minutes (%)", color=INK2)
    ax.set_title(f"{ctrl:.0%} of delay minutes are controllable by the airline", loc="left", fontsize=12, color=INK)
    style(ax)
    fig.tight_layout()
    fig.savefig(OUT / "charts" / "cause_mix.png", dpi=150)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 4))
    x = range(1, len(ap) + 1)
    ax.plot(x, ap["cumulative_share"] * 100, color=BLUE, linewidth=2)
    ax.axhline(50, color=INK2, linestyle=":", linewidth=1)
    ax.axvline(n_half, color=INK2, linestyle=":", linewidth=1)
    ax.set_xlabel("Airports, ranked by delay minutes", color=INK2)
    ax.set_ylabel("Cumulative share of delay minutes (%)", color=INK2)
    ax.set_title(f"{n_half} of {len(ap)} airports generate half of all delay minutes", loc="left", fontsize=12, color=INK)
    style(ax)
    fig.tight_layout()
    fig.savefig(OUT / "charts" / "airport_pareto.png", dpi=150)
    plt.close(fig)
    print("\nSaved: outputs/tableau/airport_bottlenecks.csv, outputs/cause_mix_by_airline.csv, outputs/charts/*.png")


if __name__ == "__main__":
    main()
