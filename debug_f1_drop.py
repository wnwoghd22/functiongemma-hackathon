import sys
sys.path.insert(0, "cactus/python/src")
from main import generate_hybrid
from benchmark import BENCHMARKS, compute_f1

cases = ["alarm_10am", "play_bohemian", "alarm_among_three", "timer_among_three", "alarm_among_five"]
for case in BENCHMARKS:
    if case["name"] in cases:
        out = generate_hybrid(case["messages"], case["tools"])
        f1 = compute_f1(out["function_calls"], case["expected_calls"])
        print(f"--- {case['name']} ---")
        print(f"Source: {out['source']}")
        print(f"Predicted: {out['function_calls']}")
        print(f"Expected:  {case['expected_calls']}")
        print(f"F1: {f1:.2f}\n")
