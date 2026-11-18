"""
scorecard.py - Phase 6: operational KPI scorecard

One scorecard row per airline, 6 KPIs, each judged against its PEER GROUP median
(Network / Low-cost / Regional), so a regional is never compared with Delta.

KPI                          better when   source
  On-time rate                 higher      efficiency (BTS definition)
  Cancellation rate            lower       efficiency
  Controllable delay min/flight lower      efficiency (carrier + late aircraft)
  Delay cost per flight        lower       costs ($100.76/min, A4A)
  Flights per FTE per month    higher      efficiency (BTS employment)
  Delay cascade ratio          lower       bottlenecks

Status: Green = at least 5% better than the peer median, Red = at least 5% worse,
Amber = in between. On-time rate uses +/-2 percentage points instead. Trend = on-time rate, latest 12 months vs the 12 months before.
Overall score = average of the 6 KPI percentile ranks within the peer group (0-100).

Outputs
  outputs/tableau/scorecard_long.csv   airline x KPI (value, target, status) for Tableau
  outputs/scorecard.csv                one row per airline

Run:  python src/scorecard.py
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
BAND = 0.05
ONTIME_BAND = 0.02   # percentage points for on-time rate

KPIS = {  # column: (label, higher_is_better, format)
    "on_time_rate": ("On-time rate", True, "{:.1%}"),
    "cancel_rate": ("Cancellation rate", False, "{:.1%}"),
    "controllable_min_per_flight": ("Controllable delay min / flight", False, "{:.1f}"),
    "cost_per_flight": ("Delay cost / flight", False, "${:,.0f}"),
    "flights_per_fte_month": ("Flights / employee / month", True, "{:.2f}"),
    "cascade_ratio": ("Delay cascade ratio", False, "{:.2f}"),
}


def status(value, target, higher, absolute=False):
    # on-time rate uses an absolute band (2 points); a 5% relative band would hide real gaps
    gap = (value - target) / (ONTIME_BAND / BAND) if absolute else (value - target) / target if target else 0
    if not higher:
        gap = -gap
    return "Green" if gap >= BAND else "Red" if gap <= -BAND else "Amber"


def main():
    eff = pd.read_csv(OUT / "airline_efficiency.csv")
    cost = pd.read_csv(OUT / "cost_by_airline.csv")[["carrier", "cost_per_flight"]]
    casc = pd.read_csv(OUT / "cause_mix_by_airline.csv")[["carrier_name", "cascade_ratio"]]
    sc = eff.merge(cost, on="carrier").merge(casc, on="carrier_name", how="left")

    # trend: on-time rate, latest 12 months vs previous 12
    m = pd.read_csv(OUT / "tableau" / "airline_monthly.csv")
    periods = sorted(m["period"].unique())
    last12, prev12 = periods[-12:], periods[-24:-12]

    def otr(d):
        return 1 - (d.delayed.sum() + d.cancelled.sum() + d.diverted.sum()) / d.flights.sum()

    trend = m.groupby("carrier").apply(
        lambda d: otr(d[d.period.isin(last12)]) - otr(d[d.period.isin(prev12)])
        if d.period.isin(prev12).any() and d.period.isin(last12).any() else float("nan"),
        include_groups=False).rename("on_time_change_pts")
    sc = sc.merge(trend, left_on="carrier", right_index=True, how="left")

    rows = []
    for col, (label, higher, fmt) in KPIS.items():
        med = sc.groupby("peer_group")[col].transform("median")
        pct = sc.groupby("peer_group")[col].rank(pct=True, ascending=higher)
        sc[f"{col}_score"] = (pct * 100).round(0)
        for i, r in sc.iterrows():
            rows.append({"carrier": r.carrier, "carrier_name": r.carrier_name, "peer_group": r.peer_group,
                         "kpi": label, "value": r[col], "peer_median": med[i],
                         "better_when": "higher" if higher else "lower",
                         "status": status(r[col], med[i], higher, col == "on_time_rate"), "value_label": fmt.format(r[col])})
    long = pd.DataFrame(rows)
    long.to_csv(OUT / "tableau" / "scorecard_long.csv", index=False)

    sc["overall_score"] = sc[[f"{c}_score" for c in KPIS]].mean(axis=1).round(0)
    counts = long.pivot_table(index="carrier", columns="status", values="kpi", aggfunc="count", fill_value=0)
    sc = sc.merge(counts, left_on="carrier", right_index=True, how="left")
    sc["trend"] = sc["on_time_change_pts"].map(
        lambda x: "n/a" if pd.isna(x) else ("Improving" if x >= 0.01 else "Worsening" if x <= -0.01 else "Flat"))
    sc = sc.sort_values(["peer_group", "overall_score"], ascending=[True, False])
    keep = ["carrier", "carrier_name", "peer_group", "overall_score"] + [c for c in ["Green", "Amber", "Red"] if c in sc] \
        + list(KPIS) + ["on_time_change_pts", "trend"]
    sc[keep].round(4).to_csv(OUT / "scorecard.csv", index=False)

    print(f"KPI SCORECARD (status vs peer-group median; +/-{BAND:.0%} band, on-time +/-2 pts; trend = on-time rate "
          f"{last12[0][:7]}..{last12[-1][:7]} vs prior 12 months)")
    for g, d in sc.groupby("peer_group", sort=False):
        print(f"\n{g.upper()}")
        show = d[["carrier_name", "overall_score"] + [c for c in ["Green", "Amber", "Red"] if c in d] + ["trend"]].copy()
        show["on_time"] = d["on_time_rate"].map("{:.1%}".format)
        show["ctrl_min"] = d["controllable_min_per_flight"].map("{:.1f}".format)
        show["cost/flight"] = d["cost_per_flight"].map("${:,.0f}".format)
        show["flights/FTE"] = d["flights_per_fte_month"].map("{:.2f}".format)
        show["change"] = d["on_time_change_pts"].map(lambda x: "" if pd.isna(x) else f"{x * 100:+.1f} pts")
        print(show.to_string(index=False))
    print("\nSaved: outputs/tableau/scorecard_long.csv, outputs/scorecard.csv")


if __name__ == "__main__":
    main()