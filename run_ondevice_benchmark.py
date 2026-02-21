"""Benchmark runner for on-device only strategy (main.py v3.0)."""
import sys
import os

import benchmark

TIMESTAMP = os.popen('date +%Y%m%d_%H%M%S').read().strip()
os.makedirs("benchmark_runs", exist_ok=True)
LOGFILE = f"benchmark_runs/benchmark_{TIMESTAMP}_ondevice_only.md"

with open(LOGFILE, "w") as f:
    f.write(f"# Benchmark Run - {TIMESTAMP}\n")
    f.write("## Strategy: On-Device Only v3.0\n")
    f.write("## Output\n```text\n")

class DualOutput:
    def __init__(self, filename):
        self.file = open(filename, "a")
        self.stdout = sys.stdout
    def write(self, data):
        self.stdout.write(data)
        self.file.write(data)
    def flush(self):
        self.stdout.flush()
        self.file.flush()

sys.stdout = DualOutput(LOGFILE)

benchmark.run_benchmark(benchmark.BENCHMARKS)

sys.stdout.file.write("```\n")
sys.stdout.file.close()
sys.stdout = sys.stdout.stdout

print(f"\nResults saved to: {LOGFILE}")
