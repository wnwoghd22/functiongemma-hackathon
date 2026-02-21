import sys, os, json
sys.path.insert(0, "cactus/python/src")

from benchmark import BENCHMARKS
import strategies.strategy_local_ensemble as strategy

for i, case in enumerate(BENCHMARKS[:5]):
    print(f"\n--- Running {case['name']} ---")
    print("Tools before hybrid:")
    print(json.dumps(case["tools"], indent=2))
    
    res = strategy.generate_hybrid(case["messages"], case["tools"])
    print(f"Final calls: {res.get('function_calls')}")
