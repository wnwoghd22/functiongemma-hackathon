import sys
import os

sys.path.insert(0, "cactus/python/src")
import strategies.strategy_local_ensemble as strategy
from benchmark import BENCHMARKS

for case in BENCHMARKS:
    if case["name"] == "weather_london":
        messages = case["messages"]
        tools = case["tools"]
        res = strategy.generate_hybrid(messages, tools)
        print("Final result:", res)
