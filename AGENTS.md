# Repository Agent Notes

## Benchmark Logging Policy
- For every benchmark execution, create a new timestamped Markdown log file.
- Use:
  - `./scripts/run_benchmark_logged.sh`
- Logs are saved to:
  - `./benchmark_runs/benchmark_YYYYMMDD_HHMMSS.md`

## Benchmark Command Convention
- Default command:
  - `python ./benchmark.py`
- You can pass a custom command to the logger script:
  - `./scripts/run_benchmark_logged.sh <custom command ...>`

## Session Hygiene
- Keep `SESSION_NOTES_YYYY-MM-DD.md` up to date with:
  - strategy changes
  - benchmark deltas
  - rationale for routing changes
