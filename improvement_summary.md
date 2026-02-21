# Improvement Summary (Up to 2026-02-22)

This document provides a quick snapshot of what was tried, what improved, and what did not.

## Scope and Constraints

- Main optimization target: internal logic of `generate_hybrid` in `main.py`.
- Submission path uploads `main.py` to the leaderboard.
- Local `benchmark.py` is useful for iteration, but scorer modifications may not transfer.

Sources:
- `/Users/jaehong/Desktop/functiongemma-hackathon/README.md:34`
- `/Users/jaehong/Desktop/functiongemma-hackathon/submit.py:22`

## Benchmark Timeline (Key Runs)

| Timestamp | Strategy | Score | Avg F1 | Avg Time | On-device |
|---|---|---:|---:|---:|---:|
| 20260221_222348 | on-device dominated (cloud unavailable) | 39.9 | 0.24 | 405.53ms | 100% |
| 20260221_222435 | `strategy_balanced` | 55.6 | 0.72 | 934.25ms | 50% |
| 20260221_225431 | `strategy_selective` v1 | 56.1 | 0.76 | 953.07ms | 43% |
| 20260222_013032 | `strategy_selective` v2.1 | 60.9 | 0.96 | 1009.84ms | 20% |
| 20260222_013630 | `strategy_tradeoff_refined` | 55.9 | 0.73 | 859.04ms | 43% |
| 20260222_014541 | `strategy_selective` v2.2 (strict scorer) | 59.2 | 0.92 | 987.49ms | 20% |
| 20260222_015239 | `strategy_selective_v21_minplus` | 60.2 | 0.96 | 1070.88ms | 20% |
| 20260222_020138 | v2.2 + local fuzzy scorer changes | 62.5 | 0.97 | 957.72ms | 20% |

Run files:
- `/Users/jaehong/Desktop/functiongemma-hackathon/benchmark_runs/benchmark_20260221_222348.md`
- `/Users/jaehong/Desktop/functiongemma-hackathon/benchmark_runs/benchmark_20260221_222435.md`
- `/Users/jaehong/Desktop/functiongemma-hackathon/benchmark_runs/benchmark_20260221_225431.md`
- `/Users/jaehong/Desktop/functiongemma-hackathon/benchmark_runs/benchmark_20260222_013032.md`
- `/Users/jaehong/Desktop/functiongemma-hackathon/benchmark_runs/benchmark_20260222_013630.md`
- `/Users/jaehong/Desktop/functiongemma-hackathon/benchmark_runs/benchmark_20260222_014541.md`
- `/Users/jaehong/Desktop/functiongemma-hackathon/benchmark_runs/benchmark_20260222_015239.md`
- `/Users/jaehong/Desktop/functiongemma-hackathon/benchmark_runs/benchmark_20260222_020138.md`

## What Clearly Worked

1. Structural fallback gates
- Parse-fail sentinel, empty-calls with tools, schema/type/range checks, multi-action under-call checks.
- This was the main jump from ~40 to ~60 score.

2. Empty-call handling
- Treating empty tool calls as cloud fallback candidates improved F1 stability.

3. Keeping hard tasks cloud-first
- Broad hard on-device expansion repeatedly reduced total score.
- Hard has high weight in scoring, so F1 loss there is expensive.

## What Underperformed

1. Global confidence-only routing
- Lowering threshold without richer signals often traded away too much F1.

2. Aggressive on-device expansion for medium/hard multi-tool tasks
- On-device ratio improved, but F1 dropped enough to reduce total score.

3. Benchmark-only fuzzy scorer upgrades (for leaderboard transfer)
- Local score can rise, but changes in `benchmark.py` are not guaranteed to affect server scoring.

## Current Best Practical Baseline

- Best transferable strategy candidate: `strategy_selective` v2.1 style routing
  (score 60.9 on local strict benchmark).
- Keep hard cloud-first unless high-confidence safe subset is proven.
- Improve with feature-based routing, not case-level hardcoding.

## Next Actionable Plan

1. Promote additional Cactus signals in `main.py`
- Keep `cloud_handoff`, `success`, and token/tps metadata from local output.

2. Replace single-threshold logic with risk-score routing
- Combine confidence + token-length + schema + multi-action coverage.

3. Add conservative output canonicalization in `main.py` only
- Normalize punctuation/case and safe time-format variants.
- Avoid semantic rewrites.

4. Validate with repeated runs
- Use timestamped benchmark logs and compare case-level deltas, not only total score.

