# Benchmark Run - 20260222_052844
## Strategy: Generalized On-Device
## Output
```text
[1/30] Running: weather_sf (easy)... F1=1.00 | 585ms | on-device
[2/30] Running: alarm_10am (easy)... F1=1.00 | 653ms | on-device
[3/30] Running: message_alice (easy)... F1=1.00 | 708ms | on-device
[4/30] Running: weather_london (easy)... F1=1.00 | 574ms | on-device
[5/30] Running: alarm_6am (easy)... F1=1.00 | 852ms | on-device
[6/30] Running: play_bohemian (easy)... F1=1.00 | 671ms | on-device
[7/30] Running: timer_5min (easy)... F1=1.00 | 604ms | on-device
[8/30] Running: reminder_meeting (easy)... F1=1.00 | 547ms | on-device
[9/30] Running: search_bob (easy)... F1=1.00 | 701ms | on-device
[10/30] Running: weather_paris (easy)... F1=1.00 | 590ms | on-device
[11/30] Running: message_among_three (medium)... F1=0.00 | 850ms | on-device
[12/30] Running: weather_among_two (medium)... F1=1.00 | 684ms | on-device
[13/30] Running: alarm_among_three (medium)... F1=0.00 | 874ms | on-device
[14/30] Running: music_among_three (medium)... F1=1.00 | 926ms | on-device
[15/30] Running: reminder_among_four (medium)... F1=1.00 | 1305ms | on-device
[16/30] Running: timer_among_three (medium)... F1=1.00 | 715ms | on-device
[17/30] Running: search_among_four (medium)... F1=1.00 | 1432ms | on-device
[18/30] Running: weather_among_four (medium)... F1=1.00 | 688ms | on-device
[19/30] Running: message_among_four (medium)... F1=1.00 | 1808ms | on-device
[20/30] Running: alarm_among_five (medium)... F1=1.00 | 889ms | on-device
[21/30] Running: message_and_weather (hard)... F1=1.00 | 1657ms | on-device
[22/30] Running: alarm_and_weather (hard)... F1=0.50 | 1619ms | on-device
[23/30] Running: timer_and_music (hard)... F1=1.00 | 1901ms | on-device
[24/30] Running: reminder_and_message (hard)... F1=1.00 | 2503ms | on-device
[25/30] Running: search_and_message (hard)... F1=1.00 | 1708ms | on-device
[26/30] Running: alarm_and_reminder (hard)... F1=0.00 | 1980ms | on-device
[27/30] Running: weather_and_music (hard)... F1=1.00 | 1985ms | on-device
[28/30] Running: message_weather_alarm (hard)... F1=1.00 | 2731ms | on-device
[29/30] Running: timer_music_reminder (hard)... F1=0.67 | 2514ms | on-device
[30/30] Running: search_message_weather (hard)... F1=0.67 | 2734ms | on-device

=== Benchmark Results ===

   # | Difficulty | Name                         |  Time (ms) |    F1 | Source
  ---+------------+------------------------------+------------+-------+---------------------
   1 | easy       | weather_sf                   |     585.32 |  1.00 | on-device
   2 | easy       | alarm_10am                   |     652.94 |  1.00 | on-device
   3 | easy       | message_alice                |     707.60 |  1.00 | on-device
   4 | easy       | weather_london               |     573.89 |  1.00 | on-device
   5 | easy       | alarm_6am                    |     852.47 |  1.00 | on-device
   6 | easy       | play_bohemian                |     670.96 |  1.00 | on-device
   7 | easy       | timer_5min                   |     604.17 |  1.00 | on-device
   8 | easy       | reminder_meeting             |     546.86 |  1.00 | on-device
   9 | easy       | search_bob                   |     700.76 |  1.00 | on-device
  10 | easy       | weather_paris                |     590.31 |  1.00 | on-device
  11 | medium     | message_among_three          |     849.79 |  0.00 | on-device
  12 | medium     | weather_among_two            |     683.98 |  1.00 | on-device
  13 | medium     | alarm_among_three            |     874.05 |  0.00 | on-device
  14 | medium     | music_among_three            |     925.67 |  1.00 | on-device
  15 | medium     | reminder_among_four          |    1304.59 |  1.00 | on-device
  16 | medium     | timer_among_three            |     715.32 |  1.00 | on-device
  17 | medium     | search_among_four            |    1432.15 |  1.00 | on-device
  18 | medium     | weather_among_four           |     688.48 |  1.00 | on-device
  19 | medium     | message_among_four           |    1808.01 |  1.00 | on-device
  20 | medium     | alarm_among_five             |     888.66 |  1.00 | on-device
  21 | hard       | message_and_weather          |    1656.54 |  1.00 | on-device
  22 | hard       | alarm_and_weather            |    1619.48 |  0.50 | on-device
  23 | hard       | timer_and_music              |    1901.39 |  1.00 | on-device
  24 | hard       | reminder_and_message         |    2502.61 |  1.00 | on-device
  25 | hard       | search_and_message           |    1708.43 |  1.00 | on-device
  26 | hard       | alarm_and_reminder           |    1979.57 |  0.00 | on-device
  27 | hard       | weather_and_music            |    1984.61 |  1.00 | on-device
  28 | hard       | message_weather_alarm        |    2730.79 |  1.00 | on-device
  29 | hard       | timer_music_reminder         |    2514.31 |  0.67 | on-device
  30 | hard       | search_message_weather       |    2734.08 |  0.67 | on-device

--- Summary ---
  easy     avg F1=1.00  avg time=648.53ms  on-device=10/10 cloud=0/10
  medium   avg F1=0.80  avg time=1017.07ms  on-device=10/10 cloud=0/10
  hard     avg F1=0.78  avg time=2133.18ms  on-device=10/10 cloud=0/10
  overall  avg F1=0.86  avg time=1266.26ms  total time=37987.82ms
           on-device=30/30 (100%)  cloud=0/30 (0%)

==================================================
  TOTAL SCORE: 74.9%
==================================================
```
