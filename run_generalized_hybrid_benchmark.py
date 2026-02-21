import sys
import os
from datetime import datetime

sys.path.insert(0, "cactus/python/src")

import benchmark
from strategies.strategy_generalized_hybrid import generate_hybrid

benchmark.generate_hybrid = generate_hybrid

results = benchmark.run_benchmark()

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = f"benchmark_runs/benchmark_{timestamp}_generalized_hybrid.md"
os.makedirs("benchmark_runs", exist_ok=True)

with open(log_file, "w") as f:
    f.write(f"# Benchmark Run - {timestamp}\n")
    f.write(f"## Strategy: Generalized Hybrid\n")
    f.write("## Output\n```text\n")
    sys.stdout.flush()
