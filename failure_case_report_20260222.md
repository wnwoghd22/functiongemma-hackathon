# Failure Case Report (2026-02-22)

## 1. Hidden Eval Failure Snapshot

- Submission result (server response):
  - `score=42.83`
  - `f1=0.1944`
  - `on_device_pct=100.0`
  - `avg_time_ms=250.7`
  - `status=complete`

Interpretation:
- `on_device_pct=100%` with very low F1 strongly indicates cloud fallback did not execute during evaluation.

## 2. Root Cause (Code-Level)

Previous `main.py` behavior:
- On the first cloud exception, code set a process-global latch:
  - `generate_hybrid._disable_cloud_fallback = True`
- After that, all remaining requests in the same run were forced to on-device.

Why this is dangerous:
- Any transient failure (DNS, timeout, quota, model availability) on one case causes total cloud blackout for the rest of the benchmark.

## 3. Implemented Fix

File changed:
- `main.py`

Changes:
1. Removed global cloud-disable latch path.
2. Added model retry list:
   - `GEMINI_MODEL_FALLBACK` (default: `gemini-2.5-flash-lite`)
   - `GEMINI_MODEL_SECONDARY` (default: `gemini-2.5-flash`)
   - `GEMINI_MODEL_TERTIARY` (optional)
3. Cloud failure now degrades per-request only:
   - returns on-device result for that case
   - attaches `cloud_error` and `cloud_models_tried`
   - does not permanently disable cloud for following cases

Expected effect:
- A single cloud error no longer collapses the whole run into `on-device=100%`.

## 4. Observable Failure Patterns (Local Bench Context)

From recent runs, failure categories were:

1. Local semantic drift with high confidence
- Example: alarm case predicted wrong minute (`10:59` instead of `10:00`) while confidence remained high.

2. Empty function calls from local model
- Especially in medium/hard tool-selection contexts.

3. Cloud output variability on strict matching
- Some message/time fields differ in formatting/paraphrase and get scored as mismatch.

## 5. Remaining Risk

- Even after latch removal, hidden-eval score can still vary due to:
  - cloud output non-determinism
  - strict argument matching
  - routing thresholds for medium cases

Recommended next verification:
1. Re-submit patched `main.py`.
2. Confirm `on_device_pct` drops below 100% (indicates cloud recovered).
3. Compare F1 change first, then tune routing thresholds.
