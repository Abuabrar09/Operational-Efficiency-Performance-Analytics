-- One row per airport: volume, delay minutes by cause and share of the network's delay
-- Window functions rank airports and compute the running (Pareto) share of all delay minutes
WITH a AS (
    SELECT airport,
           MAX(airport_name)          AS airport_name,
           MAX(airport_state)         AS state,
           SUM(arr_flights)           AS flights,
           SUM(arr_del15)             AS delayed,
           SUM(arr_cancelled)         AS cancelled,
           SUM(arr_diverted)          AS diverted,
           SUM(arr_delay)             AS delay_min,
           SUM(carrier_delay)         AS carrier_min,
           SUM(weather_delay)         AS weather_min,
           SUM(nas_delay)             AS nas_min,
           SUM(late_aircraft_delay)   AS late_aircraft_min,
           SUM(controllable_delay)    AS controllable_min
    FROM delays
    GROUP BY airport
)
SELECT *,
       ROUND(1.0 - (delayed + cancelled + diverted) / flights, 4)        AS on_time_rate,
       ROUND(delay_min / flights, 2)                                     AS delay_min_per_flight,
       RANK() OVER (ORDER BY delay_min DESC)                             AS delay_rank,
       ROUND(SUM(delay_min) OVER (ORDER BY delay_min DESC
             ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)
             / SUM(delay_min) OVER (), 4)                                AS cumulative_share
FROM a
ORDER BY delay_min DESC;
