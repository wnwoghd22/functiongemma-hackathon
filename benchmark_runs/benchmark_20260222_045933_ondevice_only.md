# Benchmark Run - 20260222_045933
## Strategy: On-Device Only v3.0
## Output
```text
[1/30] Running: weather_sf (easy)... F1=1.00 | 380ms | on-device
[2/30] Running: alarm_10am (easy)... F1=1.00 | 437ms | on-device
[3/30] Running: message_alice (easy)... F1=1.00 | 511ms | on-device
[4/30] Running: weather_london (easy)... F1=1.00 | 0ms | on-device
[5/30] Running: alarm_6am (easy)... F1=1.00 | 562ms | on-device
[6/30] Running: play_bohemian (easy)... F1=1.00 | 457ms | on-device
[7/30] Running: timer_5min (easy)... F1=1.00 | 206ms | on-device
[8/30] Running: reminder_meeting (easy)... F1=0.00 | 503ms | on-device
[9/30] Running: search_bob (easy)... F1=1.00 | 314ms | on-device
[10/30] Running: weather_paris (easy)... F1=1.00 | 598ms | on-device
[11/30] Running: message_among_three (medium)... F1=1.00 | 0ms | on-device
[12/30] Running: weather_among_two (medium)... F1=1.00 | 403ms | on-device
[13/30] Running: alarm_among_three (medium)... F1=1.00 | 490ms | on-device
[14/30] Running: music_among_three (medium)... F1=0.00 | 515ms | on-device
[15/30] Running: reminder_among_four (medium)... F1=1.00 | 595ms | on-device
[16/30] Running: timer_among_three (medium)... F1=1.00 | 0ms | on-device
[17/30] Running: search_among_four (medium)... F1=1.00 | 428ms | on-device
[18/30] Running: weather_among_four (medium)... F1=1.00 | 214ms | on-device
[19/30] Running: message_among_four (medium)... F1=1.00 | 1035ms | on-device
[20/30] Running: alarm_among_five (medium)... F1=1.00 | 559ms | on-device
[21/30] Running: message_and_weather (hard)... F1=1.00 | 427ms | on-device
[22/30] Running: alarm_and_weather (hard)... F1=1.00 | 492ms | on-device
[23/30] Running: timer_and_music (hard)... F1=1.00 | 697ms | on-device
[24/30] Running: reminder_and_message (hard)... F1=1.00 | 1442ms | on-device
[25/30] Running: search_and_message (hard)... F1=0.50 | 950ms | on-device
[26/30] Running: alarm_and_reminder (hard)... F1=1.00 | 1150ms | on-device
[27/30] Running: weather_and_music (hard)... F1=1.00 | 740ms | on-device
[28/30] Running: message_weather_alarm (hard)... F1=0.80 | 718ms | on-device
[29/30] Running: timer_music_reminder (hard)... F1=0.80 | 753ms | on-device
[30/30] Running: search_message_weather (hard)... F1=0.40 | 450ms | on-device

=== Benchmark Results ===

   # | Difficulty | Name                         |  Time (ms) |    F1 | Source
  ---+------------+------------------------------+------------+-------+---------------------
   1 | easy       | weather_sf                   |     379.78 |  1.00 | on-device
   2 | easy       | alarm_10am                   |     436.69 |  1.00 | on-device
   3 | easy       | message_alice                |     510.79 |  1.00 | on-device
   4 | easy       | weather_london               |       0.00 |  1.00 | on-device
   5 | easy       | alarm_6am                    |     561.92 |  1.00 | on-device
   6 | easy       | play_bohemian                |     457.38 |  1.00 | on-device
   7 | easy       | timer_5min                   |     206.28 |  1.00 | on-device
   8 | easy       | reminder_meeting             |     502.69 |  0.00 | on-device
   9 | easy       | search_bob                   |     313.64 |  1.00 | on-device
  10 | easy       | weather_paris                |     597.99 |  1.00 | on-device
  11 | medium     | message_among_three          |       0.00 |  1.00 | on-device
  12 | medium     | weather_among_two            |     403.44 |  1.00 | on-device
  13 | medium     | alarm_among_three            |     489.79 |  1.00 | on-device
  14 | medium     | music_among_three            |     514.64 |  0.00 | on-device
  15 | medium     | reminder_among_four          |     595.17 |  1.00 | on-device
  16 | medium     | timer_among_three            |       0.00 |  1.00 | on-device
  17 | medium     | search_among_four            |     427.55 |  1.00 | on-device
  18 | medium     | weather_among_four           |     214.46 |  1.00 | on-device
  19 | medium     | message_among_four           |    1034.85 |  1.00 | on-device
  20 | medium     | alarm_among_five             |     559.48 |  1.00 | on-device
  21 | hard       | message_and_weather          |     427.27 |  1.00 | on-device
  22 | hard       | alarm_and_weather            |     491.98 |  1.00 | on-device
  23 | hard       | timer_and_music              |     697.34 |  1.00 | on-device
  24 | hard       | reminder_and_message         |    1442.01 |  1.00 | on-device
  25 | hard       | search_and_message           |     949.77 |  0.50 | on-device
  26 | hard       | alarm_and_reminder           |    1149.95 |  1.00 | on-device
  27 | hard       | weather_and_music            |     739.96 |  1.00 | on-device
  28 | hard       | message_weather_alarm        |     718.15 |  0.80 | on-device
  29 | hard       | timer_music_reminder         |     753.12 |  0.80 | on-device
  30 | hard       | search_message_weather       |     450.47 |  0.40 | on-device

--- Summary ---
  easy     avg F1=0.90  avg time=396.72ms  on-device=10/10 cloud=0/10
  medium   avg F1=0.90  avg time=423.94ms  on-device=10/10 cloud=0/10
  hard     avg F1=0.85  avg time=782.00ms  on-device=10/10 cloud=0/10
  overall  avg F1=0.88  avg time=534.22ms  total time=16026.56ms
           on-device=30/30 (100%)  cloud=0/30 (0%)

==================================================
  TOTAL SCORE: 78.8%
==================================================
```
