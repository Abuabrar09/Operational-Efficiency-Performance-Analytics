# Operational Efficiency & Performance Analytics — US Airlines

**How much do flight delays cost US airlines, where do they come from, and which airlines run efficiently?**
An end-to-end operations analytics project on official US Department of Transportation data: data quality checks in Python, KPI logic in SQL, cost and bottleneck analysis, workforce efficiency, and a peer-group KPI scorecard, delivered as a 3-page Tableau dashboard.

**Live dashboard:** [Airline Operations Performance Dashboard (Tableau Public)](https://public.tableau.com/app/profile/abrar.ahmed.syed4247/viz/AirlineOperationsPerformanceDashboard/CostofDelays)

**Tools:** Python (pandas, matplotlib), SQL (SQLite: CTEs, window functions), Tableau Public

---

## Key findings

| | Finding |
|---|---|
| 💰 **Cost** | Delays cost airlines an estimated **$43.0B over 44 months** (~$11.7B a year, **$1,547 per flight**). Yearly cost is rising: $10.3B (2023) → $11.1B (2024) → $12.6B (2025). |
| 🛠️ **Controllable** | **74% of delay minutes are controllable** by the airline: late-arriving aircraft (40.5%) and carrier issues such as crew and maintenance (33.6%). Air traffic is 19.7%, extreme weather only 6.1%. |
| 📍 **Bottlenecks** | **17 of 375 airports cause half of all delay minutes**, led by ORD and DFW. Among busy airports, SFO (71.1%) and FLL (71.9%) have the worst on-time rates. |
| 📅 **Seasonality** | July averages **$1.52B** in delay cost vs **$667M** in October: summer costs more than 2× autumn. |
| 👥 **Efficiency** | Delta and American have nearly the same workforce (~103K vs ~102K FTE) and productivity (0.82 vs 0.79 flights per FTE per month), but Delta is on time **80.7% vs 73.3%** with **9.7 vs 17.0** controllable delay minutes per flight. |
| ⚖️ **Trade-off** | Frontier is the most productive low-cost airline (2.19 flights/FTE) but has the worst on-time rate (69.2%). Horizon Air has the best on-time rate overall (82.0%). |
| 🚦 **Scorecard** | Among network airlines, Hawaiian scores highest (90) and American lowest (23, with 5 of 6 KPIs Red). Spirit's on-time rate fell 10.6 points year over year, and most airlines are trending worse. |

### Recommendations
1. **Attack the delay cascade first.** Late-arriving aircraft is the #1 cause. More schedule buffer at hub banks and faster aircraft turns cut delay for every later flight in the day.
2. **Benchmark American against Delta.** Same scale and staffing, but ~7 points lower on-time and ~7 more controllable minutes per flight: an operations gap, not a staffing gap.
3. **Focus recovery resources on the 17 bottleneck airports**, especially in June–August, when half of the year's delay cost happens.
4. **Use the scorecard monthly.** Each Red cell shows exactly which KPI an airline should fix, compared with its own peer group.

---

## Dashboard

| Page | What it shows |
|---|---|
| **1. Cost of Delays** | Total cost, % controllable, cost per flight; monthly controllable vs uncontrollable cost; cost by airline and peer group |
| **2. Bottlenecks** | Delay causes, top 17 airports with running share (Pareto), average cost by month |
| **3. Efficiency & Scorecard** | Productivity vs reliability scatter; 21 airlines × 6 KPIs coloured Green / Amber / Red against the peer-group median |

---

## Data

| Dataset | Source | Grain |
|---|---|---|
| Airline On-Time Delay Causes | US DOT, Bureau of Transportation Statistics (BTS) | airline × airport × month |
| Schedule P-1(a) Employees | BTS Form 41 traffic and employment data | airline × month (full-time equivalent employees) |

---

## Method

**Phase 1–2: Data quality (`src/clean.py`)**
Checks for duplicate rows and duplicate keys, empty rows, blanks, negative values and logical errors (for example, delayed flights greater than total flights). Cause minutes are reconciled to the total delay, airline names are standardised to their latest name, and every check is logged to `outputs/data_quality_log.csv`. Clean data is loaded into SQLite.

**Phase 3: Cost (`sql/airline_monthly.sql`, `src/costs.py`)**
Delay cost = delay minutes × **$100.76**, the A4A 2024 average direct cost per aircraft block minute (crew, fuel, maintenance, ownership). This is an upper bound, because some delay happens at the gate; passenger time is excluded.
*Controllable* = carrier + late-arriving aircraft. *Not controllable* = weather + air traffic (NAS) + security.

**Phase 4: Bottlenecks (`sql/airport_bottlenecks.sql`, `src/bottlenecks.py`)**
Airport Pareto with `RANK()` and a running `SUM() OVER` window for cumulative share; cause mix per airline; delay cascade ratio = late-aircraft minutes ÷ carrier minutes.

**Phase 5: Workforce efficiency (`src/efficiency.py`)**
Joins monthly FTEs to flights. Airlines are compared only **within peer groups** (Network, Low-cost, Regional), because FTEs cover the whole workforce while the flights are domestic only, and regional airlines rely on partners for ground work.

**Phase 6: KPI scorecard (`src/scorecard.py`)**
6 KPIs: on-time rate, cancellation rate, controllable delay min/flight, delay cost/flight, flights per FTE, cascade ratio.
Status vs peer median: within ±5% = Amber (on-time rate: ±2 points), better = Green, worse = Red. Overall score = average percentile rank within the peer group. Trend = on-time rate, last 12 months vs the prior 12.
On-time rate follows the BTS definition: 1 − (delayed 15+ min + cancelled + diverted) ÷ flights.

**Phase 7: Tableau feed (`src/build_tableau_data.py`)**
Writes one Excel workbook (`outputs/tableau/operations_dashboard.xlsx`) with 5 sheets for the dashboard.

---

## Repository structure

```
├── data/raw/                     BTS delay causes + employment files (one per year)
├── sql/                          airline_monthly.sql, airport_bottlenecks.sql
├── src/                          clean → costs → bottlenecks → efficiency → scorecard → build_tableau_data
├── outputs/                      data quality log, cost, cause mix, efficiency, scorecard CSVs
│   ├── tableau/                  dashboard feed (CSV + operations_dashboard.xlsx)
│   └── charts/                   PNG charts from each phase
└── requirements.txt
```

## How to run

```bash
pip install -r requirements.txt
python src/clean.py
python src/costs.py
python src/bottlenecks.py
python src/efficiency.py
python src/scorecard.py
python src/build_tableau_data.py
```

## Limitations
- Delay cost is an estimate from an industry-average rate, not airline-reported cost.
- Employment counts include international and non-flight staff, so flights per FTE is only comparable within a peer group.
- BTS delay causes are reported by the airlines themselves.

---

**Abrar Ahmed Syed** · [LinkedIn](https://www.linkedin.com/in/abrar313) · [Portfolio](https://abuabrar09.github.io) · [Tableau Public](https://public.tableau.com/app/profile/abrar.ahmed.syed4247)
