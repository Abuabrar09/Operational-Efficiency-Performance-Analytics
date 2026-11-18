"""
build_tableau_data.py - Phase 7: one Excel workbook for the Tableau dashboard

  Airline_Monthly     airline x month: flights, delays, cancellations, minutes and $ by cause, FTE
  Airports            one row per airport: volume, on-time, minutes by cause, Pareto share
  Scorecard           one row per airline: 6 KPIs, overall score, trend
  Scorecard_Long      airline x KPI: value, peer median, Green/Amber/Red status
  Cause_Mix           airline x cause: share of delay minutes (long format)

Run:  python src/build_tableau_data.py
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
T = OUT / "tableau"
CAUSE_LABELS = {"carrier_min": "Carrier (crew, maintenance, ops)", "late_aircraft_min": "Late-arriving aircraft",
                "nas_min": "Air traffic / airspace", "weather_min": "Extreme weather", "security_min": "Security"}


def main():
    m = pd.read_csv(T / "airline_monthly.csv")
    eff = pd.read_csv(T / "airline_efficiency_monthly.csv")[["carrier", "period", "fte", "peer_group"]]
    m = m.merge(eff, on=["carrier", "period"], how="left")
    m["on_time_flights"] = m["flights"] - m["delayed"] - m["cancelled"] - m["diverted"]
    m["controllable"] = m["carrier_min"] + m["late_aircraft_min"]

    cause = m.groupby(["carrier", "carrier_name", "peer_group"])[list(CAUSE_LABELS)].sum().reset_index()
    cause = cause.melt(id_vars=["carrier", "carrier_name", "peer_group"], var_name="cause", value_name="minutes")
    cause["cause"] = cause["cause"].map(CAUSE_LABELS)
    cause["controllable"] = cause["cause"].isin(["Carrier (crew, maintenance, ops)", "Late-arriving aircraft"]) \
        .map({True: "Controllable", False: "Not controllable"})

    sheets = {
        "Airline_Monthly": m,
        "Airports": pd.read_csv(T / "airport_bottlenecks.csv"),
        "Scorecard": pd.read_csv(OUT / "scorecard.csv"),
        "Scorecard_Long": pd.read_csv(T / "scorecard_long.csv"),
        "Cause_Mix": cause,
    }
    path = T / "operations_dashboard.xlsx"
    with pd.ExcelWriter(path, engine="openpyxl") as xl:
        for name, df in sheets.items():
            df.to_excel(xl, sheet_name=name, index=False)
    for name, df in sheets.items():
        print(f"  {name:<16}{len(df):>7,} rows  {df.shape[1]:>3} columns")
    print(f"\nSaved: {path.relative_to(ROOT).as_posix()}")


if __name__ == "__main__":
    main()