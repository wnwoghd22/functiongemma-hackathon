# Benchmark Run - 20260222_050407
## Strategy: Pure Local Ensemble
## Output
```text
[1/30] Running: weather_sf (easy)... F1=1.00 | 483ms | on-device
[2/30] Running: alarm_10am (easy)... F1=1.00 | 1090ms | on-device (retry 1)
[3/30] Running: message_alice (easy)... F1=1.00 | 523ms | on-device
[4/30] Running: weather_london (easy)... F1=1.00 | 786ms | on-device (retry 1)
[5/30] Running: alarm_6am (easy)... F1=0.00 | 3043ms | on-device (failed validation)
[6/30] Running: play_bohemian (easy)... F1=1.00 | 495ms | on-device
[7/30] Running: timer_5min (easy)... F1=1.00 | 423ms | on-device
[8/30] Running: reminder_meeting (easy)... F1=0.00 | 867ms | on-device
[9/30] Running: search_bob (easy)... JSONDECODE ERROR: {"success":true,"error":null,"cloud_handoff":false,"response":"","function_calls":[{"name":"search_contacts","arguments":{"query":}}],"confidence":1.0000,"time_to_first_token_ms":121.90,"total_time_ms":229.19,"prefill_tps":1189.53,"decode_tps":74.56,"ram_usage_mb":69.35,"prefill_tokens":145,"decode_tokens":9,"total_tokens":154}
F1=0.00 | 1461ms | on-device (failed validation)
[10/30] Running: weather_paris (easy)... F1=1.00 | 428ms | on-device
[11/30] Running: message_among_three (medium)... JSONDECODE ERROR: {"success":true,"error":null,"cloud_handoff":false,"response":"","function_calls":[{"name":"send_message","arguments":{"message":"Hi John, I hope your day is going well.']}{recipient:","John<escape>}":}}],"confidence":0.9874,"time_to_first_token_ms":266.84,"total_time_ms":705.22,"prefill_tps":1135.50,"decode_tps":63.87,"ram_usage_mb":71.22,"prefill_tokens":303,"decode_tokens":29,"total_tokens":332}
JSONDECODE ERROR: {"success":true,"error":null,"cloud_handoff":false,"response":"","function_calls":[{"name":"send_message","arguments":{"recipient":"John","message":,"Hello there! I hope your day is doing well. thank you!<start_function_declaration>}":}}],"confidence":0.9882,"time_to_first_token_ms":238.58,"total_time_ms":731.50,"prefill_tps":1286.77,"decode_tps":62.89,"ram_usage_mb":73.66,"prefill_tokens":307,"decode_tokens":32,"total_tokens":339}
F1=0.00 | 2359ms | on-device (failed validation)
[12/30] Running: weather_among_two (medium)... F1=0.00 | 1414ms | on-device (failed validation)
[13/30] Running: alarm_among_three (medium)... F1=0.00 | 1905ms | on-device (retry 2)
[14/30] Running: music_among_three (medium)... F1=0.00 | 2447ms | on-device (failed validation)
[15/30] Running: reminder_among_four (medium)... F1=0.00 | 999ms | on-device
[16/30] Running: timer_among_three (medium)... F1=1.00 | 578ms | on-device
[17/30] Running: search_among_four (medium)... F1=0.00 | 2174ms | on-device (failed validation)
[18/30] Running: weather_among_four (medium)... F1=1.00 | 608ms | on-device
[19/30] Running: message_among_four (medium)... F1=0.00 | 4117ms | on-device (failed validation)
[20/30] Running: alarm_among_five (medium)... F1=1.00 | 741ms | on-device
[21/30] Running: message_and_weather (hard)... JSONDECODE ERROR: {"success":true,"error":null,"cloud_handoff":false,"response":"","function_calls":[{"name":"send_message","arguments":{"message":,"Hi there, Bob! I hope you'imshed well in London today.}":}}],"confidence":0.9541,"time_to_first_token_ms":240.85,"total_time_ms":674.22,"prefill_tps":1299.55,"decode_tps":57.69,"ram_usage_mb":79.94,"prefill_tokens":313,"decode_tokens":26,"total_tokens":339}
F1=0.00 | 2628ms | on-device (failed validation)
[22/30] Running: alarm_and_weather (hard)... JSONDECODE ERROR: {"success":true,"error":null,"cloud_handoff":false,"response":"","function_calls":[{"name":"set_alarm","arguments":{"hour":07`,"minute":30}}],"confidence":0.9957,"time_to_first_token_ms":285.12,"total_time_ms":559.33,"prefill_tps":1111.81,"decode_tps":58.35,"ram_usage_mb":75.94,"prefill_tokens":317,"decode_tokens":17,"total_tokens":334}
F1=0.00 | 1982ms | on-device (failed validation)
[23/30] Running: timer_and_music (hard)... JSONDECODE ERROR: {"success":true,"error":null,"cloud_handoff":false,"response":"","function_calls":[{"name":"set_timer","arguments":{"minutes：20}":}}],"confidence":0.9986,"time_to_first_token_ms":311.20,"total_time_ms":498.42,"prefill_tps":1063.61,"decode_tps":58.76,"ram_usage_mb":76.35,"prefill_tokens":331,"decode_tokens":12,"total_tokens":343}
F1=0.00 | 1944ms | on-device (failed validation)
[24/30] Running: reminder_and_message (hard)... JSONDECODE ERROR: {"success":true,"error":null,"cloud_handoff":false,"response":"","function_calls":[{"name":"create_reminder","arguments":{"time":"24:05","title":}}],"confidence":0.9995,"time_to_first_token_ms":369.15,"total_time_ms":700.45,"prefill_tps":1094.41,"decode_tps":54.33,"ram_usage_mb":79.44,"prefill_tokens":404,"decode_tokens":19,"total_tokens":423}
F1=0.00 | 3007ms | on-device (failed validation)
[25/30] Running: search_and_message (hard)... JSONDECODE ERROR: {"success":true,"error":null,"cloud_handoff":false,"response":"","function_calls":[{"name":"search_contacts","arguments":{"query":}}],"confidence":1.0000,"time_to_first_token_ms":273.20,"total_time_ms":415.93,"prefill_tps":1218.87,"decode_tps":56.05,"ram_usage_mb":78.22,"prefill_tokens":333,"decode_tokens":9,"total_tokens":342}
F1=0.67 | 1897ms | on-device (failed validation)
[26/30] Running: alarm_and_reminder (hard)... F1=0.00 | 2319ms | on-device (failed validation)
[27/30] Running: weather_and_music (hard)... JSONDECODE ERROR: {"success":true,"error":null,"cloud_handoff":false,"response":"","function_calls":[{"name":"getweather(location:"Miami")","arguments":{}}],"confidence":0.9926,"time_to_first_token_ms":288.93,"total_time_ms":471.16,"prefill_tps":1131.75,"decode_tps":54.88,"ram_usage_mb":76.61,"prefill_tokens":327,"decode_tokens":11,"total_tokens":338}
F1=0.00 | 1943ms | on-device (failed validation)
[28/30] Running: message_weather_alarm (hard)... JSONDECODE ERROR: {"success":true,"error":null,"cloud_handoff":false,"response":"","function_calls":[{"name":"send_message:","arguments":{"message":}}],"confidence":1.0000,"time_to_first_token_ms":386.23,"total_time_ms":535.81,"prefill_tps":1087.42,"decode_tps":53.48,"ram_usage_mb":77.72,"prefill_tokens":420,"decode_tokens":9,"total_tokens":429}
F1=0.00 | 2194ms | on-device (failed validation)
[29/30] Running: timer_music_reminder (hard)... F1=0.00 | 2528ms | on-device (failed validation)
[30/30] Running: search_message_weather (hard)... JSONDECODE ERROR: {"success":true,"error":null,"cloud_handoff":false,"response":"","function_calls":[{"name":"search_contacts","arguments":{"query":'JAKE'}}],"confidence":0.9840,"time_to_first_token_ms":348.50,"total_time_ms":624.68,"prefill_tps":1210.89,"decode_tps":50.69,"ram_usage_mb":83.02,"prefill_tokens":422,"decode_tokens":15,"total_tokens":437}
F1=0.00 | 3091ms | on-device (failed validation)

=== Benchmark Results ===

   # | Difficulty | Name                         |  Time (ms) |    F1 | Source
  ---+------------+------------------------------+------------+-------+---------------------
   1 | easy       | weather_sf                   |     482.97 |  1.00 | on-device
   2 | easy       | alarm_10am                   |    1090.17 |  1.00 | on-device (retry 1)
   3 | easy       | message_alice                |     523.12 |  1.00 | on-device
   4 | easy       | weather_london               |     785.81 |  1.00 | on-device (retry 1)
   5 | easy       | alarm_6am                    |    3043.20 |  0.00 | on-device (failed validation)
   6 | easy       | play_bohemian                |     495.20 |  1.00 | on-device
   7 | easy       | timer_5min                   |     423.43 |  1.00 | on-device
   8 | easy       | reminder_meeting             |     867.16 |  0.00 | on-device
   9 | easy       | search_bob                   |    1460.89 |  0.00 | on-device (failed validation)
  10 | easy       | weather_paris                |     428.39 |  1.00 | on-device
  11 | medium     | message_among_three          |    2359.03 |  0.00 | on-device (failed validation)
  12 | medium     | weather_among_two            |    1413.72 |  0.00 | on-device (failed validation)
  13 | medium     | alarm_among_three            |    1904.64 |  0.00 | on-device (retry 2)
  14 | medium     | music_among_three            |    2447.06 |  0.00 | on-device (failed validation)
  15 | medium     | reminder_among_four          |     999.26 |  0.00 | on-device
  16 | medium     | timer_among_three            |     578.20 |  1.00 | on-device
  17 | medium     | search_among_four            |    2174.08 |  0.00 | on-device (failed validation)
  18 | medium     | weather_among_four           |     608.35 |  1.00 | on-device
  19 | medium     | message_among_four           |    4117.25 |  0.00 | on-device (failed validation)
  20 | medium     | alarm_among_five             |     741.19 |  1.00 | on-device
  21 | hard       | message_and_weather          |    2628.40 |  0.00 | on-device (failed validation)
  22 | hard       | alarm_and_weather            |    1982.04 |  0.00 | on-device (failed validation)
  23 | hard       | timer_and_music              |    1944.34 |  0.00 | on-device (failed validation)
  24 | hard       | reminder_and_message         |    3006.74 |  0.00 | on-device (failed validation)
  25 | hard       | search_and_message           |    1896.98 |  0.67 | on-device (failed validation)
  26 | hard       | alarm_and_reminder           |    2318.52 |  0.00 | on-device (failed validation)
  27 | hard       | weather_and_music            |    1942.71 |  0.00 | on-device (failed validation)
  28 | hard       | message_weather_alarm        |    2194.39 |  0.00 | on-device (failed validation)
  29 | hard       | timer_music_reminder         |    2528.18 |  0.00 | on-device (failed validation)
  30 | hard       | search_message_weather       |    3091.48 |  0.00 | on-device (failed validation)

--- Summary ---
  easy     avg F1=0.70  avg time=960.03ms  on-device=6/10 cloud=4/10
  medium   avg F1=0.30  avg time=1734.28ms  on-device=4/10 cloud=6/10
  hard     avg F1=0.07  avg time=2353.38ms  on-device=0/10 cloud=10/10
  overall  avg F1=0.36  avg time=1682.56ms  total time=50476.91ms
           on-device=10/30 (33%)  cloud=20/30 (67%)

==================================================
  TOTAL SCORE: 21.8%
==================================================
```
