-- One row per airline per month: volume, delays and minutes by cause
SELECT carrier,
       carrier_name,
       period,
       year,
       month,
       SUM(arr_flights)           AS flights,
       SUM(arr_del15)             AS delayed,
       SUM(arr_cancelled)         AS cancelled,
       SUM(arr_diverted)          AS diverted,
       SUM(arr_delay)             AS delay_min,
       SUM(carrier_delay)         AS carrier_min,
       SUM(weather_delay)         AS weather_min,
       SUM(nas_delay)             AS nas_min,
       SUM(security_delay)        AS security_min,
       SUM(late_aircraft_delay)   AS late_aircraft_min,
       SUM(controllable_delay)    AS controllable_min
FROM delays
GROUP BY carrier, carrier_name, period, year, month
ORDER BY carrier, period;
