import sys, os
sys.path.insert(0, "cactus/python/src")

from benchmark import BENCHMARKS
import strategies.strategy_local_ensemble as strategy

for i, case in enumerate(BENCHMARKS[:5]):
    print(f"Running {case['name']}")
    res = strategy.generate_hybrid(case["messages"], case["tools"])
    print(res)
