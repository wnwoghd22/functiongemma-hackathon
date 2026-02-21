# Hidden Submission Failure Inference (2026-02-22)

## Scope
- Hidden eval does not expose per-case traces.
- This document infers likely repeated failure classes from:
  - real submission aggregates,
  - leaderboard snapshots,
  - repeated low-F1 local patterns.

## Observed Real Submission Outcomes

| Time (UTC) | Score | F1 | On-device | Avg Time (ms) | Evidence |
|---|---:|---:|---:|---:|---|
| 2026-02-21T18:38:29Z | 42.83 | 0.1944 | 100% | 250.7 | `failure_case_report_20260222.md` |
| 2026-02-21T20:41:27Z | 70.6 | 0.7933 | 100% | 3757.26 | `SESSION_NOTES_2026-02-21.md`, leaderboard.json |
| pending | - | - | - | - | submission id `da948b8d073d4adea3da13afbd89c1f1` (queued) |

## Repeated Signals Seen in Hidden Submissions

1. `on_device_pct=100%` repeated across materially different scores.
- Implication: cloud route is either not triggered, or triggered then degraded back to local often enough to look fully local.

2. F1 can collapse to near on-device-only baseline.
- 42.83 run (`F1=0.1944`) is consistent with "cloud path effectively absent" behavior.

3. Hidden runtime can be much slower than local benchmark for similar strategy family.
- Example gap documented: local ~1385ms vs hidden ~3757ms.
- Implication: hidden prompts likely include longer/more ambiguous wording, causing heavier local decode and argument extraction stress.

## Repeated Low-F1 Local Families (Proxy for Hidden Risk)

Aggregated from these runs:
- `benchmark_runs/benchmark_20260222_053740.md`
- `benchmark_runs/benchmark_20260222_054900.md`
- `benchmark_runs/benchmark_20260222_060250.md`
- `benchmark_runs/benchmark_20260222_061111.md`
- `benchmark_runs/benchmark_20260222_062606.md`
- `benchmark_runs/benchmark_20260222_062904.md`
- `benchmark_runs/benchmark_20260222_063843.md`
- `benchmark_runs/benchmark_20260222_064040.md`

Most repeated sub-1.0 F1 cases:
- `alarm_among_three`: 7/9
- `reminder_among_four`: 7/9
- `alarm_and_weather`: 7/9
- `search_and_message`: 7/9
- `alarm_and_reminder`: 7/9
- `timer_music_reminder`: 6/9
- `message_among_three`: 4/9

Interpretation:
- Multi-intent and multi-argument composition tasks are the stable weak spot.
- This aligns with hidden-eval underperformance when cloud is not reliably used.

## Inferred Hidden Failure Classes

### H1) Cloud path non-materialization in hidden runtime (High confidence)
Evidence:
- Hidden runs repeatedly show 100% on-device.
- Very low hidden F1 run matches local on-device-only behavior.

Likely mechanisms:
- hidden-specific schema edge cases,
- SDK/config compatibility mismatch,
- per-case cloud exception with local degrade fallback.

### H2) Multi-action under-call or partial-call outputs (High confidence)
Evidence:
- Repeated low-F1 local cases are dominated by multi-tool/multi-intent tasks.
- F1 values around 0.50/0.67 match partial correctness patterns.

### H3) Argument lexical mismatch under strict scoring (High confidence)
Evidence:
- Existing analyses note strict field-level matching sensitivity.
- Message/reminder/time fields are most exposed to small format drift.

### H4) Time-expression normalization drift (Medium confidence)
Evidence:
- Alarm/reminder clusters fail repeatedly.
- Hidden prompts likely include broader natural language time expressions.

### H5) Over-conservative fallback gating (Medium confidence)
Evidence:
- External network benchmark with current `main.py` reached only ~3% cloud use (`benchmark_20260222_064040.md`).
- If hidden data is harder, this can leave too many risky cases local.

## Practical Inference Rules for Next Submissions

Use submission aggregate metrics as diagnostics:

1. If `on_device_pct=100%` and `F1 <= 0.30`:
- Treat as effective cloud failure / non-use.
- Prioritize cloud path reliability and trigger observability.

2. If `on_device_pct=100%` and `F1 ~ 0.75-0.85`:
- Local strategy is decent but weak on repeated multi-intent families.
- Prioritize targeted local fixes for those families.

3. If `on_device_pct < 100%` and `F1 rises significantly`:
- Cloud path is alive and helping.
- Then optimize routing selectivity (avoid over-triggering easy cases).

## Actionable Next Focus (No Hidden Labels Required)

1. Keep a narrow fallback target set for known weak families only.
2. Improve multi-action call preservation (avoid losing valid secondary calls).
3. Add stronger argument sanity checks before accepting local output for alarm/reminder/message mixes.
4. Keep cloud fallback reason codes explicit so aggregate behavior can be inferred from next run-level metrics.

## Confidence and Limits
- Confidence is high for structural trends (cloud non-materialization, multi-intent weakness).
- Confidence is medium for exact hidden prompt types and schema complexity, because hidden per-case traces are unavailable.
