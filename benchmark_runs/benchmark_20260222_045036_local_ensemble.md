# Benchmark Run - 20260222_045036
## Strategy: Pure Local Ensemble
## Output
```text
[1/30] Running: weather_sf (easy)... F1=1.00 | 423ms | on-device
[2/30] Running: alarm_10am (easy)... F1=1.00 | 948ms | on-device (retry 1)
[3/30] Running: message_alice (easy)... F1=0.00 | 1424ms | on-device (failed validation)
[4/30] Running: weather_london (easy)... F1=0.00 | 1347ms | on-device (failed validation)
[5/30] Running: alarm_6am (easy)... F1=0.00 | 3246ms | on-device (failed validation)
[6/30] Running: play_bohemian (easy)... F1=1.00 | 499ms | on-device
[7/30] Running: timer_5min (easy)... F1=1.00 | 388ms | on-device
[8/30] Running: reminder_meeting (easy)... F1=0.00 | 889ms | on-device
[9/30] Running: search_bob (easy)... F1=1.00 | 1092ms | on-device (retry 1)
[10/30] Running: weather_paris (easy)... F1=1.00 | 1755ms | on-device (retry 2)
[11/30] Running: message_among_three (medium)... F1=0.00 | 1944ms | on-device (failed validation)
[12/30] Running: weather_among_two (medium)... F1=1.00 | 497ms | on-device
[13/30] Running: alarm_among_three (medium)... F1=0.00 | 2005ms | on-device (failed validation)
[14/30] Running: music_among_three (medium)... F1=0.00 | 1913ms | on-device (failed validation)
[15/30] Running: reminder_among_four (medium)... F1=0.00 | 2741ms | on-device (failed validation)
[16/30] Running: timer_among_three (medium)... F1=0.00 | 1831ms | on-device (failed validation)
[17/30] Running: search_among_four (medium)... F1=0.00 | 2459ms | on-device (failed validation)
[18/30] Running: weather_among_four (medium)... F1=1.00 | 701ms | on-device
[19/30] Running: message_among_four (medium)... F1=0.00 | 4117ms | on-device (failed validation)
[20/30] Running: alarm_among_five (medium)... F1=1.00 | 778ms | on-device
[21/30] Running: message_and_weather (hard)... F1=0.00 | 2371ms | on-device (failed validation)
[22/30] Running: alarm_and_weather (hard)... F1=0.67 | 1862ms | on-device (failed validation)
[23/30] Running: timer_and_music (hard)... F1=0.00 | 1850ms | on-device (failed validation)
[24/30] Running: reminder_and_message (hard)... F1=0.00 | 2934ms | on-device (failed validation)
[25/30] Running: search_and_message (hard)... F1=0.00 | 1903ms | on-device (failed validation)
[26/30] Running: alarm_and_reminder (hard)... F1=0.00 | 2306ms | on-device (failed validation)
[27/30] Running: weather_and_music (hard)... F1=0.00 | 2208ms | on-device (failed validation)
[28/30] Running: message_weather_alarm (hard)... F1=0.00 | 2225ms | on-device (failed validation)
[29/30] Running: timer_music_reminder (hard)... F1=0.00 | 2432ms | on-device (failed validation)
[30/30] Running: search_message_weather (hard)... F1=0.00 | 2819ms | on-device (failed validation)

=== Benchmark Results ===

   # | Difficulty | Name                         |  Time (ms) |    F1 | Source
  ---+------------+------------------------------+------------+-------+---------------------
   1 | easy       | weather_sf                   |     422.89 |  1.00 | on-device
   2 | easy       | alarm_10am                   |     947.91 |  1.00 | on-device (retry 1)
   3 | easy       | message_alice                |    1423.59 |  0.00 | on-device (failed validation)
   4 | easy       | weather_london               |    1347.49 |  0.00 | on-device (failed validation)
   5 | easy       | alarm_6am                    |    3245.92 |  0.00 | on-device (failed validation)
   6 | easy       | play_bohemian                |     498.96 |  1.00 | on-device
   7 | easy       | timer_5min                   |     387.78 |  1.00 | on-device
   8 | easy       | reminder_meeting             |     888.88 |  0.00 | on-device
   9 | easy       | search_bob                   |    1092.38 |  1.00 | on-device (retry 1)
  10 | easy       | weather_paris                |    1755.23 |  1.00 | on-device (retry 2)
  11 | medium     | message_among_three          |    1944.17 |  0.00 | on-device (failed validation)
  12 | medium     | weather_among_two            |     497.23 |  1.00 | on-device
  13 | medium     | alarm_among_three            |    2004.54 |  0.00 | on-device (failed validation)
  14 | medium     | music_among_three            |    1912.82 |  0.00 | on-device (failed validation)
  15 | medium     | reminder_among_four          |    2741.42 |  0.00 | on-device (failed validation)
  16 | medium     | timer_among_three            |    1830.69 |  0.00 | on-device (failed validation)
  17 | medium     | search_among_four            |    2458.55 |  0.00 | on-device (failed validation)
  18 | medium     | weather_among_four           |     701.34 |  1.00 | on-device
  19 | medium     | message_among_four           |    4117.37 |  0.00 | on-device (failed validation)
  20 | medium     | alarm_among_five             |     777.79 |  1.00 | on-device
  21 | hard       | message_and_weather          |    2370.98 |  0.00 | on-device (failed validation)
  22 | hard       | alarm_and_weather            |    1861.88 |  0.67 | on-device (failed validation)
  23 | hard       | timer_and_music              |    1850.00 |  0.00 | on-device (failed validation)
  24 | hard       | reminder_and_message         |    2934.19 |  0.00 | on-device (failed validation)
  25 | hard       | search_and_message           |    1902.89 |  0.00 | on-device (failed validation)
  26 | hard       | alarm_and_reminder           |    2306.48 |  0.00 | on-device (failed validation)
  27 | hard       | weather_and_music            |    2207.69 |  0.00 | on-device (failed validation)
  28 | hard       | message_weather_alarm        |    2225.16 |  0.00 | on-device (failed validation)
  29 | hard       | timer_music_reminder         |    2432.42 |  0.00 | on-device (failed validation)
  30 | hard       | search_message_weather       |    2818.81 |  0.00 | on-device (failed validation)

--- Summary ---
  easy     avg F1=0.60  avg time=1201.10ms  on-device=4/10 cloud=6/10
  medium   avg F1=0.30  avg time=1898.59ms  on-device=3/10 cloud=7/10
  hard     avg F1=0.07  avg time=2291.05ms  on-device=0/10 cloud=10/10
  overall  avg F1=0.32  avg time=1796.91ms  total time=53907.45ms
           on-device=7/30 (23%)  cloud=23/30 (77%)

==================================================
  TOTAL SCORE: 18.8%
==================================================
```
