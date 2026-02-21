import sys
sys.path.insert(0, "cactus/python/src")
from main import generate_hybrid
from benchmark import BENCHMARKS, compute_f1

cases = []
for case in BENCHMARKS:
    out = generate_hybrid(case["messages"], case["tools"])
    f1 = compute_f1(out["function_calls"], case["expected_calls"])
    source = out["source"]
    if source == "on-device" and f1 < 1.0:
        cases.append((case["name"], out["function_calls"], case["expected_calls"], out.get("fallback_reason")))
    elif source == "cloud (fallback)" and f1 < 1.0:
        cases.append((case["name"], out["function_calls"], case["expected_calls"], out.get("fallback_reason")))

print("--- Failures Analysis ---")
for name, pred, exp, reason in cases:
    print(f"[{name}] (Reason: {reason})")
    print(f"Predicted: {pred}")
    print(f"Expected:  {exp}\n")
