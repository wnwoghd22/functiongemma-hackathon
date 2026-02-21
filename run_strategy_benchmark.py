import sys
import os

# Monkey patch benchmark to use our strategy
import benchmark
import strategies.strategy_prompt_multisignal as strategy

benchmark.generate_hybrid = strategy.generate_hybrid

TIMESTAMP = os.popen('date +%Y%m%d_%H%M%S').read().strip()
LOGFILE = f"benchmark_runs/benchmark_{TIMESTAMP}_prompt_multisignal.md"

with open(LOGFILE, "w") as f:
    f.write(f"# Benchmark Run - {TIMESTAMP}\n")
    f.write("## Strategy: Prompt + Multi-Signal\n")
    f.write("## Output\n```text\n")

# Hook stdout to both print and write to file
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

# Run benchmark
benchmark.run_benchmark(benchmark.BENCHMARKS)

sys.stdout.file.write("```\n")
sys.stdout.file.close()
sys.stdout = sys.stdout.stdout
