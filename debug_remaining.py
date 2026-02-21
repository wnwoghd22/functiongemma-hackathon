"""Debug remaining failures."""
import sys, json
sys.path.insert(0, "cactus/python/src")
from main import generate_hybrid
import benchmark

failing = ["reminder_meeting", "music_among_three", "search_and_message", "message_weather_alarm", "timer_music_reminder", "search_message_weather"]

for case in benchmark.BENCHMARKS:
    if case["name"] not in failing:
        continue
    result = generate_hybrid(case["messages"], case["tools"])
    f1 = benchmark.compute_f1(result["function_calls"], case["expected_calls"])
    print(f"\n{'='*60}")
    print(f"Case: {case['name']} | F1={f1:.2f}")
    print(f"User: {case['messages'][0]['content']}")
    print(f"Expected: {json.dumps(case['expected_calls'], indent=2)}")
    print(f"Got:      {json.dumps(result['function_calls'], indent=2)}")
