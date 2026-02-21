import sys
import json
sys.path.insert(0, "cactus/python/src")
import benchmark
import strategies.strategy_generalized_ondevice as strategy

benchmark.generate_hybrid = strategy.generate_hybrid

for case in benchmark.BENCHMARKS:
    if case["name"] in ["weather_sf", "alarm_10am", "message_alice", "weather_london", "alarm_6am", "play_bohemian", "timer_5min"]:
        print(f"\n--- {case['name']} ---")
        try:
            res = strategy.generate_hybrid(case["messages"], case["tools"])
            print("Calls:", res.get("function_calls"))
            f1 = benchmark.compute_f1(res.get("function_calls", []), case["expected_calls"])
            print("Expected:", case["expected_calls"])
            print("F1:", f1)
        except Exception as e:
            print("Error:", e)
