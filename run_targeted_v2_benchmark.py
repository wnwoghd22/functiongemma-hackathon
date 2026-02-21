#!/usr/bin/env python3
"""Benchmark runner for strategy_targeted_v2.py"""
import sys
sys.path.insert(0, ".")

from strategies.strategy_targeted_v2 import generate_hybrid
import benchmark

benchmark.generate_hybrid = generate_hybrid

if __name__ == "__main__":
    results = benchmark.run_benchmark()
