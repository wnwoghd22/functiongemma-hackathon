# Benchmark Run - 20260222_033425
## Strategy: Prompt + Multi-Signal
## Output
```text
[1/30] Running: weather_sf (easy)... F1=1.00 | 289ms | on-device
[2/30] Running: alarm_10am (easy)... F1=0.00 | 338ms | on-device
[3/30] Running: message_alice (easy)... F1=1.00 | 1223ms | cloud (fallback)
[4/30] Running: weather_london (easy)... F1=1.00 | 300ms | on-device
[5/30] Running: alarm_6am (easy)... F1=1.00 | 1501ms | cloud (fallback)
[6/30] Running: play_bohemian (easy)... F1=1.00 | 367ms | on-device
[7/30] Running: timer_5min (easy)... F1=1.00 | 960ms | cloud (fallback)
[8/30] Running: reminder_meeting (easy)... F1=1.00 | 737ms | cloud (fallback)
[9/30] Running: search_bob (easy)... F1=1.00 | 320ms | on-device
[10/30] Running: weather_paris (easy)... F1=1.00 | 315ms | on-device
[11/30] Running: message_among_three (medium)... F1=1.00 | 1426ms | cloud (fallback)
[12/30] Running: weather_among_two (medium)... F1=1.00 | 738ms | cloud (fallback)
[13/30] Running: alarm_among_three (medium)... F1=1.00 | 1363ms | cloud (fallback)
[14/30] Running: music_among_three (medium)... F1=1.00 | 1291ms | cloud (fallback)
[15/30] Running: reminder_among_four (medium)... F1=1.00 | 719ms | cloud (fallback)
[16/30] Running: timer_among_three (medium)... F1=1.00 | 1011ms | cloud (fallback)
[17/30] Running: search_among_four (medium)... F1=1.00 | 1389ms | cloud (fallback)
[18/30] Running: weather_among_four (medium)... F1=1.00 | 484ms | on-device
[19/30] Running: message_among_four (medium)... F1=0.00 | 1623ms | cloud (fallback)
[20/30] Running: alarm_among_five (medium)... F1=1.00 | 476ms | cloud (fallback)
[21/30] Running: message_and_weather (hard)... F1=1.00 | 987ms | cloud (fallback)
[22/30] Running: alarm_and_weather (hard)... F1=1.00 | 1409ms | cloud (fallback)
[23/30] Running: timer_and_music (hard)... F1=1.00 | 1182ms | cloud (fallback)
[24/30] Running: reminder_and_message (hard)... F1=1.00 | 1317ms | cloud (fallback)
[25/30] Running: search_and_message (hard)... F1=1.00 | 756ms | cloud (fallback)
[26/30] Running: alarm_and_reminder (hard)... F1=1.00 | 1388ms | cloud (fallback)
[27/30] Running: weather_and_music (hard)... F1=1.00 | 1241ms | cloud (fallback)
[28/30] Running: message_weather_alarm (hard)... F1=0.67 | 875ms | cloud (fallback)
[29/30] Running: timer_music_reminder (hard)... F1=1.00 | 1149ms | cloud (fallback)
[30/30] Running: search_message_weather (hard)... F1=1.00 | 974ms | cloud (fallback)

=== Benchmark Results ===

   # | Difficulty | Name                         |  Time (ms) |    F1 | Source
  ---+------------+------------------------------+------------+-------+---------------------
   1 | easy       | weather_sf                   |     289.14 |  1.00 | on-device
   2 | easy       | alarm_10am                   |     337.85 |  0.00 | on-device
   3 | easy       | message_alice                |    1222.57 |  1.00 | cloud (fallback)
   4 | easy       | weather_london               |     300.04 |  1.00 | on-device
   5 | easy       | alarm_6am                    |    1501.36 |  1.00 | cloud (fallback)
   6 | easy       | play_bohemian                |     366.84 |  1.00 | on-device
   7 | easy       | timer_5min                   |     960.19 |  1.00 | cloud (fallback)
   8 | easy       | reminder_meeting             |     737.34 |  1.00 | cloud (fallback)
   9 | easy       | search_bob                   |     319.78 |  1.00 | on-device
  10 | easy       | weather_paris                |     315.36 |  1.00 | on-device
  11 | medium     | message_among_three          |    1426.08 |  1.00 | cloud (fallback)
  12 | medium     | weather_among_two            |     738.45 |  1.00 | cloud (fallback)
  13 | medium     | alarm_among_three            |    1362.55 |  1.00 | cloud (fallback)
  14 | medium     | music_among_three            |    1291.33 |  1.00 | cloud (fallback)
  15 | medium     | reminder_among_four          |     719.27 |  1.00 | cloud (fallback)
  16 | medium     | timer_among_three            |    1011.16 |  1.00 | cloud (fallback)
  17 | medium     | search_among_four            |    1389.32 |  1.00 | cloud (fallback)
  18 | medium     | weather_among_four           |     483.95 |  1.00 | on-device
  19 | medium     | message_among_four           |    1622.90 |  0.00 | cloud (fallback)
  20 | medium     | alarm_among_five             |     476.08 |  1.00 | cloud (fallback)
  21 | hard       | message_and_weather          |     987.09 |  1.00 | cloud (fallback)
  22 | hard       | alarm_and_weather            |    1409.44 |  1.00 | cloud (fallback)
  23 | hard       | timer_and_music              |    1181.52 |  1.00 | cloud (fallback)
  24 | hard       | reminder_and_message         |    1316.53 |  1.00 | cloud (fallback)
  25 | hard       | search_and_message           |     755.76 |  1.00 | cloud (fallback)
  26 | hard       | alarm_and_reminder           |    1387.80 |  1.00 | cloud (fallback)
  27 | hard       | weather_and_music            |    1241.35 |  1.00 | cloud (fallback)
  28 | hard       | message_weather_alarm        |     875.31 |  0.67 | cloud (fallback)
  29 | hard       | timer_music_reminder         |    1149.06 |  1.00 | cloud (fallback)
  30 | hard       | search_message_weather       |     973.68 |  1.00 | cloud (fallback)

--- Summary ---
  easy     avg F1=0.90  avg time=635.05ms  on-device=6/10 cloud=4/10
  medium   avg F1=0.90  avg time=1052.11ms  on-device=1/10 cloud=9/10
  hard     avg F1=0.97  avg time=1127.75ms  on-device=0/10 cloud=10/10
  overall  avg F1=0.92  avg time=938.30ms  total time=28149.11ms
           on-device=7/30 (23%)  cloud=23/30 (77%)

==================================================
  TOTAL SCORE: 59.7%
==================================================
```
