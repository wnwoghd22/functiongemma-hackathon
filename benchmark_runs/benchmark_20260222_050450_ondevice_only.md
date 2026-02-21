# Benchmark Run - 20260222_050450
## Strategy: On-Device Only v3.0
## Output
```text
[1/30] Running: weather_sf (easy)... F1=1.00 | 438ms | on-device
[2/30] Running: alarm_10am (easy)... F1=1.00 | 469ms | on-device
[3/30] Running: message_alice (easy)... F1=1.00 | 528ms | on-device
[4/30] Running: weather_london (easy)... F1=1.00 | 0ms | on-device
[5/30] Running: alarm_6am (easy)... F1=1.00 | 947ms | on-device
[6/30] Running: play_bohemian (easy)... F1=1.00 | 495ms | on-device
[7/30] Running: timer_5min (easy)... F1=1.00 | 254ms | on-device
[8/30] Running: reminder_meeting (easy)... F1=1.00 | 404ms | on-device
[9/30] Running: search_bob (easy)... F1=1.00 | 455ms | on-device
[10/30] Running: weather_paris (easy)... F1=1.00 | 505ms | on-device
[11/30] Running: message_among_three (medium)... F1=1.00 | 733ms | on-device
[12/30] Running: weather_among_two (medium)... F1=1.00 | 0ms | on-device
[13/30] Running: alarm_among_three (medium)... F1=1.00 | 542ms | on-device
[14/30] Running: music_among_three (medium)... F1=1.00 | 615ms | on-device
[15/30] Running: reminder_among_four (medium)... F1=1.00 | 663ms | on-device
[16/30] Running: timer_among_three (medium)... F1=1.00 | 432ms | on-device
[17/30] Running: search_among_four (medium)... F1=1.00 | 469ms | on-device
[18/30] Running: weather_among_four (medium)... F1=1.00 | 402ms | on-device
[19/30] Running: message_among_four (medium)... F1=1.00 | 772ms | on-device
[20/30] Running: alarm_among_five (medium)... F1=1.00 | 496ms | on-device
[21/30] Running: message_and_weather (hard)... F1=1.00 | 437ms | on-device
[22/30] Running: alarm_and_weather (hard)... F1=1.00 | 828ms | on-device
[23/30] Running: timer_and_music (hard)... F1=1.00 | 751ms | on-device
[24/30] Running: reminder_and_message (hard)... F1=1.00 | 1864ms | on-device
[25/30] Running: search_and_message (hard)... F1=1.00 | 1070ms | on-device
[26/30] Running: alarm_and_reminder (hard)... F1=1.00 | 468ms | on-device
[27/30] Running: weather_and_music (hard)... F1=1.00 | 338ms | on-device
[28/30] Running: message_weather_alarm (hard)... F1=1.00 | 1773ms | on-device
[29/30] Running: timer_music_reminder (hard)... F1=1.00 | 1669ms | on-device
[30/30] Running: search_message_weather (hard)... F1=1.00 | 478ms | on-device

=== Benchmark Results ===

   # | Difficulty | Name                         |  Time (ms) |    F1 | Source
  ---+------------+------------------------------+------------+-------+---------------------
   1 | easy       | weather_sf                   |     437.81 |  1.00 | on-device
   2 | easy       | alarm_10am                   |     468.70 |  1.00 | on-device
   3 | easy       | message_alice                |     527.95 |  1.00 | on-device
   4 | easy       | weather_london               |       0.00 |  1.00 | on-device
   5 | easy       | alarm_6am                    |     946.81 |  1.00 | on-device
   6 | easy       | play_bohemian                |     494.72 |  1.00 | on-device
   7 | easy       | timer_5min                   |     253.60 |  1.00 | on-device
   8 | easy       | reminder_meeting             |     403.57 |  1.00 | on-device
   9 | easy       | search_bob                   |     455.36 |  1.00 | on-device
  10 | easy       | weather_paris                |     504.56 |  1.00 | on-device
  11 | medium     | message_among_three          |     733.15 |  1.00 | on-device
  12 | medium     | weather_among_two            |       0.00 |  1.00 | on-device
  13 | medium     | alarm_among_three            |     541.66 |  1.00 | on-device
  14 | medium     | music_among_three            |     615.00 |  1.00 | on-device
  15 | medium     | reminder_among_four          |     662.56 |  1.00 | on-device
  16 | medium     | timer_among_three            |     431.81 |  1.00 | on-device
  17 | medium     | search_among_four            |     468.77 |  1.00 | on-device
  18 | medium     | weather_among_four           |     402.11 |  1.00 | on-device
  19 | medium     | message_among_four           |     772.22 |  1.00 | on-device
  20 | medium     | alarm_among_five             |     495.83 |  1.00 | on-device
  21 | hard       | message_and_weather          |     437.24 |  1.00 | on-device
  22 | hard       | alarm_and_weather            |     828.45 |  1.00 | on-device
  23 | hard       | timer_and_music              |     751.40 |  1.00 | on-device
  24 | hard       | reminder_and_message         |    1864.26 |  1.00 | on-device
  25 | hard       | search_and_message           |    1070.20 |  1.00 | on-device
  26 | hard       | alarm_and_reminder           |     467.78 |  1.00 | on-device
  27 | hard       | weather_and_music            |     338.29 |  1.00 | on-device
  28 | hard       | message_weather_alarm        |    1772.60 |  1.00 | on-device
  29 | hard       | timer_music_reminder         |    1669.27 |  1.00 | on-device
  30 | hard       | search_message_weather       |     478.33 |  1.00 | on-device

--- Summary ---
  easy     avg F1=1.00  avg time=449.31ms  on-device=10/10 cloud=0/10
  medium   avg F1=1.00  avg time=512.31ms  on-device=10/10 cloud=0/10
  hard     avg F1=1.00  avg time=967.78ms  on-device=10/10 cloud=0/10
  overall  avg F1=1.00  avg time=643.13ms  total time=19294.01ms
           on-device=30/30 (100%)  cloud=0/30 (0%)

==================================================
  TOTAL SCORE: 85.3%
==================================================
```
