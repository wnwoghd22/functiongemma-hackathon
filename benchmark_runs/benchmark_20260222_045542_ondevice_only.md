# Benchmark Run - 20260222_045542
## Strategy: On-Device Only v3.0
## Output
```text
[1/30] Running: weather_sf (easy)... F1=1.00 | 411ms | on-device
[2/30] Running: alarm_10am (easy)... F1=1.00 | 488ms | on-device
[3/30] Running: message_alice (easy)... F1=1.00 | 579ms | on-device
[4/30] Running: weather_london (easy)... F1=1.00 | 439ms | on-device
[5/30] Running: alarm_6am (easy)... F1=0.00 | 739ms | on-device
[6/30] Running: play_bohemian (easy)... F1=0.00 | 0ms | on-device
[7/30] Running: timer_5min (easy)... F1=1.00 | 385ms | on-device
[8/30] Running: reminder_meeting (easy)... F1=0.00 | 404ms | on-device
[9/30] Running: search_bob (easy)... F1=0.00 | 601ms | on-device
[10/30] Running: weather_paris (easy)... F1=0.00 | 0ms | on-device
[11/30] Running: message_among_three (medium)... F1=0.00 | 598ms | on-device
[12/30] Running: weather_among_two (medium)... F1=1.00 | 460ms | on-device
[13/30] Running: alarm_among_three (medium)... F1=0.00 | 594ms | on-device
[14/30] Running: music_among_three (medium)... F1=0.00 | 442ms | on-device
[15/30] Running: reminder_among_four (medium)... F1=0.00 | 1376ms | on-device
[16/30] Running: timer_among_three (medium)... F1=0.00 | 472ms | on-device
[17/30] Running: search_among_four (medium)... F1=1.00 | 467ms | on-device
[18/30] Running: weather_among_four (medium)... F1=0.00 | 459ms | on-device
[19/30] Running: message_among_four (medium)... F1=1.00 | 634ms | on-device
[20/30] Running: alarm_among_five (medium)... F1=1.00 | 497ms | on-device
[21/30] Running: message_and_weather (hard)... F1=0.67 | 1277ms | on-device
[22/30] Running: alarm_and_weather (hard)... F1=0.00 | 1039ms | on-device
[23/30] Running: timer_and_music (hard)... F1=0.00 | 348ms | on-device
[24/30] Running: reminder_and_message (hard)... F1=0.00 | 2514ms | on-device
[25/30] Running: search_and_message (hard)... F1=0.00 | 473ms | on-device
[26/30] Running: alarm_and_reminder (hard)... F1=0.00 | 802ms | on-device
[27/30] Running: weather_and_music (hard)... F1=0.00 | 701ms | on-device
[28/30] Running: message_weather_alarm (hard)... F1=0.00 | 931ms | on-device
[29/30] Running: timer_music_reminder (hard)... F1=0.40 | 838ms | on-device
[30/30] Running: search_message_weather (hard)... F1=0.50 | 577ms | on-device

=== Benchmark Results ===

   # | Difficulty | Name                         |  Time (ms) |    F1 | Source
  ---+------------+------------------------------+------------+-------+---------------------
   1 | easy       | weather_sf                   |     411.03 |  1.00 | on-device
   2 | easy       | alarm_10am                   |     487.68 |  1.00 | on-device
   3 | easy       | message_alice                |     578.58 |  1.00 | on-device
   4 | easy       | weather_london               |     438.67 |  1.00 | on-device
   5 | easy       | alarm_6am                    |     738.55 |  0.00 | on-device
   6 | easy       | play_bohemian                |       0.00 |  0.00 | on-device
   7 | easy       | timer_5min                   |     385.30 |  1.00 | on-device
   8 | easy       | reminder_meeting             |     403.60 |  0.00 | on-device
   9 | easy       | search_bob                   |     600.97 |  0.00 | on-device
  10 | easy       | weather_paris                |       0.00 |  0.00 | on-device
  11 | medium     | message_among_three          |     598.26 |  0.00 | on-device
  12 | medium     | weather_among_two            |     460.32 |  1.00 | on-device
  13 | medium     | alarm_among_three            |     593.99 |  0.00 | on-device
  14 | medium     | music_among_three            |     442.28 |  0.00 | on-device
  15 | medium     | reminder_among_four          |    1375.51 |  0.00 | on-device
  16 | medium     | timer_among_three            |     472.11 |  0.00 | on-device
  17 | medium     | search_among_four            |     467.46 |  1.00 | on-device
  18 | medium     | weather_among_four           |     459.43 |  0.00 | on-device
  19 | medium     | message_among_four           |     634.10 |  1.00 | on-device
  20 | medium     | alarm_among_five             |     497.20 |  1.00 | on-device
  21 | hard       | message_and_weather          |    1276.71 |  0.67 | on-device
  22 | hard       | alarm_and_weather            |    1039.17 |  0.00 | on-device
  23 | hard       | timer_and_music              |     348.08 |  0.00 | on-device
  24 | hard       | reminder_and_message         |    2513.75 |  0.00 | on-device
  25 | hard       | search_and_message           |     473.17 |  0.00 | on-device
  26 | hard       | alarm_and_reminder           |     801.72 |  0.00 | on-device
  27 | hard       | weather_and_music            |     700.93 |  0.00 | on-device
  28 | hard       | message_weather_alarm        |     930.61 |  0.00 | on-device
  29 | hard       | timer_music_reminder         |     837.91 |  0.40 | on-device
  30 | hard       | search_message_weather       |     577.02 |  0.50 | on-device

--- Summary ---
  easy     avg F1=0.50  avg time=404.44ms  on-device=10/10 cloud=0/10
  medium   avg F1=0.40  avg time=600.07ms  on-device=10/10 cloud=0/10
  hard     avg F1=0.16  avg time=949.91ms  on-device=10/10 cloud=0/10
  overall  avg F1=0.35  avg time=651.47ms  total time=19544.11ms
           on-device=30/30 (100%)  cloud=0/30 (0%)

==================================================
  TOTAL SCORE: 43.5%
==================================================
```
