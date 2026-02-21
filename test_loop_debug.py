import sys, os
sys.path.insert(0, "cactus/python/src")

from benchmark import BENCHMARKS
import strategies.strategy_local_ensemble as strategy

for i, case in enumerate(BENCHMARKS[:5]):
    print(f"\n--- Running {case['name']} ---")
    
    # We will trace inside _should_retry_local by modifying the local copy temporarily
    original_retry = strategy._should_retry_local
    
    def traced_retry(local, messages, tools):
        res = original_retry(local, messages, tools)
        print(f"[{case['name']}] _should_retry_local returned: {res}")
        print(f"Local calls: {local.get('function_calls')}")
        return res
        
    strategy._should_retry_local = traced_retry
    
    res = strategy.generate_hybrid(case["messages"], case["tools"])
    print(f"Final source: {res.get('source')}")
    
    strategy._should_retry_local = original_retry
