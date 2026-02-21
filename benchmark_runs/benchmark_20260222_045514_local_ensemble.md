# Benchmark Run - 20260222_045514
## Strategy: Pure Local Ensemble
## Output
```text
[1/30] Running: weather_sf (easy)... F1=1.00 | 386ms | on-device
[2/30] Running: alarm_10am (easy)... F1=1.00 | 924ms | on-device (retry 1)
[3/30] Running: message_alice (easy)... F1=1.00 | 1445ms | on-device (retry 2)
[4/30] Running: weather_london (easy)... F1=0.00 | 1175ms | on-device (failed validation)
[5/30] Running: alarm_6am (easy)... F1=0.00 | 2389ms | on-device (failed validation)
[6/30] Running: play_bohemian (easy)... F1=1.00 | 450ms | on-device
[7/30] Running: timer_5min (easy)... F1=1.00 | 427ms | on-device
[8/30] Running: reminder_meeting (easy)... F1=0.00 | 790ms | on-device
[9/30] Running: search_bob (easy)... F1=0.00 | 761ms | on-device (retry 1)
[10/30] Running: weather_paris (easy)... F1=0.00 | 1141ms | on-device (failed validation)
[11/30] Running: message_among_three (medium)... F1=0.00 | 2375ms | on-device (retry 2)
[12/30] Running: weather_among_two (medium)... F1=1.00 | 854ms | on-device (retry 1)
[13/30] Running: alarm_among_three (medium)... F1=0.00 | 1835ms | on-device (failed validation)
[14/30] Running: music_among_three (medium)... F1=0.00 | 1977ms | on-device (failed validation)
[15/30] Running: reminder_among_four (medium)... F1=0.00 | 895ms | on-device
[16/30] Running: timer_among_three (medium)... F1=1.00 | 498ms | on-device
[17/30] Running: search_among_four (medium)... F1=0.00 | 2900ms | on-device (failed validation)
[18/30] Running: weather_among_four (medium)... F1=1.00 | 687ms | on-device
[19/30] Running: message_among_four (medium)... F1=0.00 | 4790ms | on-device (failed validation)
[20/30] Running: alarm_among_five (medium)... F1=1.00 | 774ms | on-device
[21/30] Running: message_and_weather (hard)... F1=0.00 | 2995ms | on-device (failed validation)
[22/30] Running: alarm_and_weather (hard)... F1=0.00 | 2067ms | on-device (failed validation)
[23/30] Running: timer_and_music (hard)... F1=0.00 | 1856ms | on-device (failed validation)
[24/30] Running: reminder_and_message (hard)... F1=0.00 | 2950ms | on-device (failed validation)
[25/30] Running: search_and_message (hard)... F1=0.67 | 1970ms | on-device (failed validation)
[26/30] Running: alarm_and_reminder (hard)... F1=0.00 | 2093ms | on-device (failed validation)
[27/30] Running: weather_and_music (hard)... F1=0.00 | 2024ms | on-device (failed validation)
[28/30] Running: message_weather_alarm (hard)... F1=0.00 | 2008ms | on-device (failed validation)
[29/30] Running: timer_music_reminder (hard)... F1=0.00 | 2357ms | on-device (failed validation)
[30/30] Running: search_message_weather (hard)... F1=0.00 | 2888ms | on-device (failed validation)

=== Benchmark Results ===

   # | Difficulty | Name                         |  Time (ms) |    F1 | Source
  ---+------------+------------------------------+------------+-------+---------------------
   1 | easy       | weather_sf                   |     386.14 |  1.00 | on-device
   2 | easy       | alarm_10am                   |     923.93 |  1.00 | on-device (retry 1)
   3 | easy       | message_alice                |    1445.06 |  1.00 | on-device (retry 2)
   4 | easy       | weather_london               |    1175.40 |  0.00 | on-device (failed validation)
   5 | easy       | alarm_6am                    |    2388.55 |  0.00 | on-device (failed validation)
   6 | easy       | play_bohemian                |     450.31 |  1.00 | on-device
   7 | easy       | timer_5min                   |     426.51 |  1.00 | on-device
   8 | easy       | reminder_meeting             |     790.07 |  0.00 | on-device
   9 | easy       | search_bob                   |     761.10 |  0.00 | on-device (retry 1)
  10 | easy       | weather_paris                |    1141.17 |  0.00 | on-device (failed validation)
  11 | medium     | message_among_three          |    2374.94 |  0.00 | on-device (retry 2)
  12 | medium     | weather_among_two            |     853.90 |  1.00 | on-device (retry 1)
  13 | medium     | alarm_among_three            |    1834.77 |  0.00 | on-device (failed validation)
  14 | medium     | music_among_three            |    1976.65 |  0.00 | on-device (failed validation)
  15 | medium     | reminder_among_four          |     895.39 |  0.00 | on-device
  16 | medium     | timer_among_three            |     498.34 |  1.00 | on-device
  17 | medium     | search_among_four            |    2900.06 |  0.00 | on-device (failed validation)
  18 | medium     | weather_among_four           |     686.70 |  1.00 | on-device
  19 | medium     | message_among_four           |    4789.83 |  0.00 | on-device (failed validation)
  20 | medium     | alarm_among_five             |     773.72 |  1.00 | on-device
  21 | hard       | message_and_weather          |    2995.05 |  0.00 | on-device (failed validation)
  22 | hard       | alarm_and_weather            |    2066.91 |  0.00 | on-device (failed validation)
  23 | hard       | timer_and_music              |    1856.15 |  0.00 | on-device (failed validation)
  24 | hard       | reminder_and_message         |    2950.47 |  0.00 | on-device (failed validation)
  25 | hard       | search_and_message           |    1970.08 |  0.67 | on-device (failed validation)
  26 | hard       | alarm_and_reminder           |    2092.67 |  0.00 | on-device (failed validation)
  27 | hard       | weather_and_music            |    2024.00 |  0.00 | on-device (failed validation)
  28 | hard       | message_weather_alarm        |    2007.60 |  0.00 | on-device (failed validation)
  29 | hard       | timer_music_reminder         |    2357.08 |  0.00 | on-device (failed validation)
  30 | hard       | search_message_weather       |    2888.43 |  0.00 | on-device (failed validation)

--- Summary ---
  easy     avg F1=0.50  avg time=988.82ms  on-device=4/10 cloud=6/10
  medium   avg F1=0.40  avg time=1758.43ms  on-device=4/10 cloud=6/10
  hard     avg F1=0.07  avg time=2320.85ms  on-device=0/10 cloud=10/10
  overall  avg F1=0.32  avg time=1689.37ms  total time=50680.99ms
           on-device=8/30 (27%)  cloud=22/30 (73%)

==================================================
  TOTAL SCORE: 20.2%
==================================================
```
