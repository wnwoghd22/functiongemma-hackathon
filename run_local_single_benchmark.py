import sys
import os
sys.path.insert(0, "cactus/python/src")

import benchmark
import strategies.strategy_local_single as strategy

benchmark.generate_hybrid = strategy.generate_hybrid
benchmark.run_benchmark(benchmark.BENCHMARKS)
