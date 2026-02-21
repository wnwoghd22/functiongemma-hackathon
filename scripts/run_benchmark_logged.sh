#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="$ROOT_DIR/benchmark_runs"
TIMESTAMP="$(date '+%Y%m%d_%H%M%S')"
LOG_FILE="$LOG_DIR/benchmark_${TIMESTAMP}.md"

mkdir -p "$LOG_DIR"

# Activate project venv when available.
if [[ -f "$ROOT_DIR/cactus/venv/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source "$ROOT_DIR/cactus/venv/bin/activate"
fi

CMD=(python "$ROOT_DIR/benchmark.py")
if [[ $# -gt 0 ]]; then
  CMD=("$@")
fi

{
  echo "# Benchmark Run - ${TIMESTAMP}"
  echo
  echo "## Command"
  echo '```bash'
  printf '%q ' "${CMD[@]}"
  echo
  echo '```'
  echo
  echo "## Output"
  echo '```text'
} > "$LOG_FILE"

set +e
"${CMD[@]}" | tee -a "$LOG_FILE"
STATUS=$?
set -e

{
  echo '```'
  echo
  echo "## Exit Status"
  echo "\`${STATUS}\`"
} >> "$LOG_FILE"

echo "Saved benchmark log: $LOG_FILE"
exit "$STATUS"
