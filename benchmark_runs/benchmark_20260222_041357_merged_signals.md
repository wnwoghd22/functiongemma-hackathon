# Benchmark Run - 20260222_041357 - Merged Multi-Signal
## Command
```bash
python3 benchmark.py
```

## Output
```text
[1/30] Running: weather_sf (easy)... F1=1.00 | 262ms | on-device
[2/30] Running: alarm_10am (easy)... F1=0.00 | 326ms | on-device
[3/30] Running: message_alice (easy)... F1=1.00 | 367ms | on-device
[4/30] Running: weather_london (easy)... F1=1.00 | 259ms | on-device
[5/30] Running: alarm_6am (easy)... F1=1.00 | 1221ms | cloud (fallback)
[6/30] Running: play_bohemian (easy)... F1=0.00 | 337ms | on-device
[7/30] Running: timer_5min (easy)... F1=1.00 | 244ms | on-device
[8/30] Running: reminder_meeting (easy)... F1=1.00 | 961ms | cloud (fallback)
[9/30] Running: search_bob (easy)... F1=1.00 | 1034ms | cloud (fallback)
[10/30] Running: weather_paris (easy)... F1=1.00 | 269ms | on-device
[11/30] Running: message_among_three (medium)... F1=1.00 | 1346ms | cloud (fallback)
[12/30] Running: weather_among_two (medium)... F1=1.00 | 955ms | cloud (fallback)
[13/30] Running: alarm_among_three (medium)... F1=1.00 | 475ms | on-device
[14/30] Running: music_among_three (medium)... F1=1.00 | 1827ms | cloud (fallback)
[15/30] Running: reminder_among_four (medium)... F1=1.00 | 1024ms | cloud (fallback)
[16/30] Running: timer_among_three (medium)... F1=0.00 | 373ms | on-device
[17/30] Running: search_among_four (medium)... F1=1.00 | 1230ms | cloud (fallback)
[18/30] Running: weather_among_four (medium)... F1=1.00 | 522ms | on-device
[19/30] Running: message_among_four (medium)... F1=1.00 | 1709ms | cloud (fallback)
[20/30] Running: alarm_among_five (medium)... F1=0.00 | 670ms | on-device
[21/30] Running: message_and_weather (hard)... F1=1.00 | 1230ms | cloud (fallback)
[22/30] Running: alarm_and_weather (hard)... F1=1.00 | 1272ms | cloud (fallback)
[23/30] Running: timer_and_music (hard)... F1=1.00 | 1268ms | cloud (fallback)
[24/30] Running: reminder_and_message (hard)... F1=1.00 | 1630ms | cloud (fallback)
[25/30] Running: search_and_message (hard)... F1=1.00 | 746ms | cloud (fallback)
[26/30] Running: alarm_and_reminder (hard)... F1=1.00 | 1253ms | cloud (fallback)
[27/30] Running: weather_and_music (hard)... F1=1.00 | 761ms | cloud (fallback)
[28/30] Running: message_weather_alarm (hard)... F1=1.00 | 594ms | cloud (fallback)
[29/30] Running: timer_music_reminder (hard)... F1=1.00 | 1765ms | cloud (fallback)
[30/30] Running: search_message_weather (hard)... F1=1.00 | 1297ms | cloud (fallback)

=== Benchmark Results ===

   # | Difficulty | Name                         |  Time (ms) |    F1 | Source
  ---+------------+------------------------------+------------+-------+---------------------
   1 | easy       | weather_sf                   |     261.75 |  1.00 | on-device
   2 | easy       | alarm_10am                   |     325.98 |  0.00 | on-device
   3 | easy       | message_alice                |     366.86 |  1.00 | on-device
   4 | easy       | weather_london               |     258.77 |  1.00 | on-device
   5 | easy       | alarm_6am                    |    1220.96 |  1.00 | cloud (fallback)
   6 | easy       | play_bohemian                |     336.60 |  0.00 | on-device
   7 | easy       | timer_5min                   |     243.95 |  1.00 | on-device
   8 | easy       | reminder_meeting             |     960.90 |  1.00 | cloud (fallback)
   9 | easy       | search_bob                   |    1034.12 |  1.00 | cloud (fallback)
  10 | easy       | weather_paris                |     269.23 |  1.00 | on-device
  11 | medium     | message_among_three          |    1345.55 |  1.00 | cloud (fallback)
  12 | medium     | weather_among_two            |     955.11 |  1.00 | cloud (fallback)
  13 | medium     | alarm_among_three            |     475.40 |  1.00 | on-device
  14 | medium     | music_among_three            |    1827.46 |  1.00 | cloud (fallback)
  15 | medium     | reminder_among_four          |    1024.48 |  1.00 | cloud (fallback)
  16 | medium     | timer_among_three            |     372.96 |  0.00 | on-device
  17 | medium     | search_among_four            |    1229.58 |  1.00 | cloud (fallback)
  18 | medium     | weather_among_four           |     522.17 |  1.00 | on-device
  19 | medium     | message_among_four           |    1709.24 |  1.00 | cloud (fallback)
  20 | medium     | alarm_among_five             |     669.72 |  0.00 | on-device
  21 | hard       | message_and_weather          |    1229.80 |  1.00 | cloud (fallback)
  22 | hard       | alarm_and_weather            |    1271.78 |  1.00 | cloud (fallback)
  23 | hard       | timer_and_music              |    1268.25 |  1.00 | cloud (fallback)
  24 | hard       | reminder_and_message         |    1630.07 |  1.00 | cloud (fallback)
  25 | hard       | search_and_message           |     746.17 |  1.00 | cloud (fallback)
  26 | hard       | alarm_and_reminder           |    1253.18 |  1.00 | cloud (fallback)
  27 | hard       | weather_and_music            |     760.74 |  1.00 | cloud (fallback)
  28 | hard       | message_weather_alarm        |     593.75 |  1.00 | cloud (fallback)
  29 | hard       | timer_music_reminder         |    1765.45 |  1.00 | cloud (fallback)
  30 | hard       | search_message_weather       |    1296.65 |  1.00 | cloud (fallback)

--- Summary ---
  easy     avg F1=0.80  avg time=527.91ms  on-device=7/10 cloud=3/10
  medium   avg F1=0.80  avg time=1013.17ms  on-device=4/10 cloud=6/10
  hard     avg F1=1.00  avg time=1181.58ms  on-device=0/10 cloud=10/10
  overall  avg F1=0.87  avg time=907.55ms  total time=27226.63ms
           on-device=11/30 (37%)  cloud=19/30 (63%)

==================================================
  TOTAL SCORE: 60.5%
==================================================
```

## Exit Status
`0`
