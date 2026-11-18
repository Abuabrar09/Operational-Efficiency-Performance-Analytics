"""
clean.py - Phase 2: data quality checks and cleaning

Reads the BTS Airline On-Time Delay Causes file (one row = one airline at one
airport in one month), checks data quality, cleans it, and loads it into
SQLite (data/processed/ops.db, table delays) for the SQL phases.

Outputs
  data/processed/ops.db               table: delays
  outputs/data_quality_log.csv        every check: rows affected and action taken

Run:  python src/clean.py
"""
import sqlite3
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "Airline_Delay_Cause.csv"
DB = ROOT / "data" / "processed" / "ops.db"
OUT = ROOT / "outputs"

CAUSES = ["carrier", "weather", "nas", "security", "late_aircraft"]
COUNT_COLS = ["arr_flights", "arr_del15"] + [f"{c}_ct" for c in CAUSES] + ["arr_cancelled", "arr_diverted"]
MIN_COLS = ["arr_delay"] + [f"{c}_delay" for c in CAUSES]
KEY = ["year", "month", "carrier", "airport"]


def main():
    OUT.mkdir(exist_ok=True)
    DB.parent.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(RAW)
    df.columns = df.columns.str.strip().str.lower()
    log = []

    def check(name, rows, action):
        log.append({"check": name, "rows_affected": int(rows), "action": action})

    check("Raw rows (airline x airport x month)", len(df), "Loaded")
    check("Months covered", df[["year", "month"]].drop_duplicates().shape[0],
          f"{df.year.min()}-{df.month[df.year == df.year.min()].min():02d} to "
          f"{df.year.max()}-{df.month[df.year == df.year.max()].max():02d}")

    # 1. exact duplicates
    dupes = int(df.duplicated().sum())
    check("Exact duplicate rows", dupes, "Removed" if dupes else "None found")
    df = df.drop_duplicates()

    # 2. same airline/airport/month reported twice with different numbers
    key_dupes = int(df.duplicated(KEY, keep=False).sum())
    check("Same airline/airport/month on more than one row", key_dupes,
          "Summed into one row" if key_dupes else "None found")
    if key_dupes:
        names = df.groupby(KEY)[["carrier_name", "airport_name"]].first()
        df = df.groupby(KEY)[COUNT_COLS + MIN_COLS].sum(min_count=1).join(names).reset_index()

    # 3. rows with no flight data (BTS leaves these blank)
    empty = int(df["arr_flights"].isna().sum() + (df["arr_flights"] == 0).sum())
    check("Rows with no arriving flights (blank or 0)", empty, "Removed")
    df = df[df["arr_flights"].fillna(0) > 0].copy()

    # 4. remaining blanks in numeric columns
    blanks = int(df[COUNT_COLS + MIN_COLS].isna().any(axis=1).sum())
    check("Rows with other blank numbers", blanks, "Filled with 0" if blanks else "None found")
    df[COUNT_COLS + MIN_COLS] = df[COUNT_COLS + MIN_COLS].fillna(0)

    # 5. negative values
    neg = int((df[COUNT_COLS + MIN_COLS] < 0).any(axis=1).sum())
    check("Rows with negative counts or minutes", neg, "Removed" if neg else "None found")
    df = df[~(df[COUNT_COLS + MIN_COLS] < 0).any(axis=1)]

    # 6. logical checks (flagged, not removed)
    over = int((df["arr_del15"] + df["arr_cancelled"] + df["arr_diverted"] > df["arr_flights"] + 0.5).sum())
    check("Delayed + cancelled + diverted > scheduled flights", over, "Flagged, kept")
    cause_min = df[[f"{c}_delay" for c in CAUSES]].sum(axis=1)
    mism = (cause_min - df["arr_delay"]).abs() > 1
    check("Cause minutes do not add up to total delay minutes", int(mism.sum()),
          "Flagged; total delay reset to the sum of causes")
    df.loc[mism, "arr_delay"] = cause_min[mism]
    cause_ct = df[[f"{c}_ct" for c in CAUSES]].sum(axis=1)
    check("Cause counts differ from delayed flights by more than 1",
          int(((cause_ct - df["arr_del15"]).abs() > 1).sum()),
          "Flagged, kept (BTS splits a delayed flight across causes)")

    # 7. one name per airline code (names change after mergers and rebrands)
    multi = df.groupby("carrier")["carrier_name"].nunique()
    renamed = multi[multi > 1]
    check("Airline codes with more than one name", len(renamed),
          "Standardized to the most recent name" + (f" ({', '.join(renamed.index)})" if len(renamed) else ""))
    latest = df.sort_values(["year", "month"]).groupby("carrier")["carrier_name"].last()
    df["carrier_name"] = df["carrier"].map(latest).str.replace(r"\s+(Inc\.|Co\.|Corp\.|LLC)$", "", regex=True).str.replace(r"\s+Network$", "", regex=True)

    # derived fields
    df["period"] = pd.to_datetime(dict(year=df.year, month=df.month, day=1)).dt.strftime("%Y-%m-%d")
    df["airport_state"] = df["airport_name"].str.extract(r",\s*([A-Z]{2}):")[0]
    df["controllable_delay"] = df["carrier_delay"] + df["late_aircraft_delay"]
    df["uncontrollable_delay"] = df["weather_delay"] + df["nas_delay"] + df["security_delay"]

    check("Clean rows", len(df), "Loaded to SQLite table delays")
    with sqlite3.connect(DB) as con:
        df.to_sql("delays", con, if_exists="replace", index=False)
        con.execute("CREATE INDEX IF NOT EXISTS ix_c ON delays(carrier, period)")
        con.execute("CREATE INDEX IF NOT EXISTS ix_a ON delays(airport, period)")

    log = pd.DataFrame(log)
    log.to_csv(OUT / "data_quality_log.csv", index=False)
    pd.set_option("display.width", 200)
    print(log.to_string(index=False))
    flights = df["arr_flights"].sum()
    print(f"\nAirlines: {df.carrier.nunique()} | Airports: {df.airport.nunique()} | "
          f"Months: {df.period.nunique()} | Flights: {flights:,.0f}")
    ontime = 1 - (df.arr_del15.sum() + df.arr_cancelled.sum() + df.arr_diverted.sum()) / flights
    print(f"On-time rate: {ontime:.1%} | "
          f"Cancelled: {df.arr_cancelled.sum() / flights:.1%} | "
          f"Delay minutes: {df.arr_delay.sum():,.0f}")
    print(f"Database: {DB.relative_to(ROOT).as_posix()}")


if __name__ == "__main__":
    main()
