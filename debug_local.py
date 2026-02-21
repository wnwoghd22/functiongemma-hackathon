import sys, os
sys.path.insert(0, "cactus/python/src")
import json
from main import generate_cactus
from benchmark import BENCHMARKS, compute_f1

for case in BENCHMARKS:
    local_out = generate_cactus(case["messages"], case["tools"])
    f1 = compute_f1(local_out["function_calls"], case["expected_calls"])
    print(f"--- {case['name']} (F1: {f1:.2f}) ---")
    print(f"Predicted: {local_out['function_calls']}")
    print(f"Expected:  {case['expected_calls']}")
    print()
