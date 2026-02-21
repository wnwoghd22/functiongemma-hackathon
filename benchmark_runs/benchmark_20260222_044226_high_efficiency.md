# Benchmark Run - 20260222_044226
## Strategy: High-Efficiency (Codex Improvements)
## Output
```text
[1/30] Running: weather_sf (easy)... F1=1.00 | 271ms | on-device
[2/30] Running: alarm_10am (easy)... F1=1.00 | 341ms | on-device
[3/30] Running: message_alice (easy)... F1=1.00 | 375ms | on-device
[4/30] Running: weather_london (easy)... F1=1.00 | 262ms | on-device
[5/30] Running: alarm_6am (easy)... F1=1.00 | 1452ms | cloud (fallback)
[6/30] Running: play_bohemian (easy)... F1=0.00 | 412ms | on-device
[7/30] Running: timer_5min (easy)... F1=1.00 | 987ms | cloud (fallback)
[8/30] Running: reminder_meeting (easy)... F1=1.00 | 817ms | cloud (fallback)
[9/30] Running: search_bob (easy)... F1=1.00 | 674ms | cloud (fallback)
[10/30] Running: weather_paris (easy)... F1=1.00 | 842ms | cloud (fallback)
[11/30] Running: message_among_three (medium)... F1=1.00 | 1427ms | cloud (fallback)
[12/30] Running: weather_among_two (medium)... F1=1.00 | 362ms | on-device
[13/30] Running: alarm_among_three (medium)... F1=1.00 | 1234ms | cloud (fallback)
[14/30] Running: music_among_three (medium)... F1=0.00 | 1537ms | cloud (fallback)
[15/30] Running: reminder_among_four (medium)... F1=1.00 | 1941ms | cloud (fallback)
[16/30] Running: timer_among_three (medium)... F1=1.00 | 1235ms | cloud (fallback)
[17/30] Running: search_among_four (medium)... F1=1.00 | 1766ms | cloud (fallback)
[18/30] Running: weather_among_four (medium)... F1=1.00 | 506ms | on-device
[19/30] Running: message_among_four (medium)... F1=1.00 | 2199ms | cloud (fallback)
[20/30] Running: alarm_among_five (medium)... F1=1.00 | 657ms | on-device
[21/30] Running: message_and_weather (hard)... F1=1.00 | 1400ms | cloud (fallback)
[22/30] Running: alarm_and_weather (hard)... F1=1.00 | 2183ms | cloud (fallback)
[23/30] Running: timer_and_music (hard)... F1=1.00 | 1813ms | cloud (fallback)
[24/30] Running: reminder_and_message (hard)... F1=1.00 | 2457ms | cloud (fallback)
[25/30] Running: search_and_message (hard)... F1=0.67 | 2891ms | cloud (fallback)
[26/30] Running: alarm_and_reminder (hard)... F1=1.00 | 1800ms | cloud (fallback)
[27/30] Running: weather_and_music (hard)... F1=0.67 | 1602ms | cloud (fallback)
[28/30] Running: message_weather_alarm (hard)... F1=1.00 | 1949ms | cloud (fallback)
[29/30] Running: timer_music_reminder (hard)... F1=1.00 | 2120ms | cloud (fallback)
[30/30] Running: search_message_weather (hard)... F1=1.00 | 2693ms | cloud (fallback)

=== Benchmark Results ===

   # | Difficulty | Name                         |  Time (ms) |    F1 | Source
  ---+------------+------------------------------+------------+-------+---------------------
   1 | easy       | weather_sf                   |     270.62 |  1.00 | on-device
   2 | easy       | alarm_10am                   |     341.37 |  1.00 | on-device
   3 | easy       | message_alice                |     375.20 |  1.00 | on-device
   4 | easy       | weather_london               |     261.83 |  1.00 | on-device
   5 | easy       | alarm_6am                    |    1452.40 |  1.00 | cloud (fallback)
   6 | easy       | play_bohemian                |     412.06 |  0.00 | on-device
   7 | easy       | timer_5min                   |     986.52 |  1.00 | cloud (fallback)
   8 | easy       | reminder_meeting             |     816.56 |  1.00 | cloud (fallback)
   9 | easy       | search_bob                   |     673.51 |  1.00 | cloud (fallback)
  10 | easy       | weather_paris                |     842.33 |  1.00 | cloud (fallback)
  11 | medium     | message_among_three          |    1426.96 |  1.00 | cloud (fallback)
  12 | medium     | weather_among_two            |     361.67 |  1.00 | on-device
  13 | medium     | alarm_among_three            |    1234.09 |  1.00 | cloud (fallback)
  14 | medium     | music_among_three            |    1537.21 |  0.00 | cloud (fallback)
  15 | medium     | reminder_among_four          |    1941.07 |  1.00 | cloud (fallback)
  16 | medium     | timer_among_three            |    1235.28 |  1.00 | cloud (fallback)
  17 | medium     | search_among_four            |    1766.11 |  1.00 | cloud (fallback)
  18 | medium     | weather_among_four           |     505.91 |  1.00 | on-device
  19 | medium     | message_among_four           |    2199.40 |  1.00 | cloud (fallback)
  20 | medium     | alarm_among_five             |     656.94 |  1.00 | on-device
  21 | hard       | message_and_weather          |    1399.90 |  1.00 | cloud (fallback)
  22 | hard       | alarm_and_weather            |    2183.48 |  1.00 | cloud (fallback)
  23 | hard       | timer_and_music              |    1812.84 |  1.00 | cloud (fallback)
  24 | hard       | reminder_and_message         |    2457.41 |  1.00 | cloud (fallback)
  25 | hard       | search_and_message           |    2890.91 |  0.67 | cloud (fallback)
  26 | hard       | alarm_and_reminder           |    1799.57 |  1.00 | cloud (fallback)
  27 | hard       | weather_and_music            |    1601.90 |  0.67 | cloud (fallback)
  28 | hard       | message_weather_alarm        |    1949.05 |  1.00 | cloud (fallback)
  29 | hard       | timer_music_reminder         |    2119.96 |  1.00 | cloud (fallback)
  30 | hard       | search_message_weather       |    2693.39 |  1.00 | cloud (fallback)

--- Summary ---
  easy     avg F1=0.90  avg time=643.24ms  on-device=5/10 cloud=5/10
  medium   avg F1=0.90  avg time=1286.46ms  on-device=3/10 cloud=7/10
  hard     avg F1=0.93  avg time=2090.84ms  on-device=0/10 cloud=10/10
  overall  avg F1=0.91  avg time=1340.18ms  total time=40205.45ms
           on-device=8/30 (27%)  cloud=22/30 (73%)

==================================================
  TOTAL SCORE: 59.7%
==================================================
```
