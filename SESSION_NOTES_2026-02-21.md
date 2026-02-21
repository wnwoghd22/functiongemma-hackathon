# FunctionGemma Hackathon Session Notes (2026-02-21)

## 1) Objective and Constraints
- Primary task: improve internal logic of `generate_hybrid` only.
- Constraint: keep `generate_hybrid` signature and return interface compatible with `benchmark.py`.
- Source refs:
  - `/Users/jaehong/Desktop/functiongemma-hackathon/README.md:34`
  - `/Users/jaehong/Desktop/functiongemma-hackathon/README.md:35`

## 2) Setup/Environment Issues Observed
- `Step 5` with `--reconvert` requires Hugging Face gated model access (`google/functiongemma-270m-it`) and HF token.
- `cactus auth` key is separate from HF token; it does not unlock gated HF model download.
- Workspace was moved, which broke venv script shebang/path references (`/Users/jaehong/Desktop/cactus/...` -> new workspace path).
- Local shell did not always inherit `GEMINI_API_KEY` unless `~/.zshrc` was sourced.

## 3) Code Change History (Current Branch)
- File changed: `/Users/jaehong/Desktop/functiongemma-hackathon/main.py`
- Change summary:
  - Wrapped cloud fallback call in `try/except` inside `generate_hybrid`.
  - Added one-run guard (`generate_hybrid._disable_cloud_fallback`) to stop repeated failing cloud calls.
  - On cloud exception, returns local result instead of crashing benchmark.
- Purpose:
  - Prevent benchmark termination when cloud model is unavailable/misconfigured.
- Current git status:
  - Modified: `main.py`

## 4) Benchmark/Failure Analysis (Observed)
- Baseline local benchmark run (shared run):
  - overall avg F1 around `0.24`
  - all requests on-device (`30/30`)
  - total score around `40.0%`
- Failure taxonomy from 30-case classification:
  - `EMPTY_CALLS`: 12
  - `PARSE_FAIL`: 7
  - `MISSING_CALLS`: 3
  - `ARG_ERROR`: 2
  - `CORRECT`: 6
- High-impact root causes:
  - Invalid JSON in model/parse output path (e.g., leading-zero numeric literals, malformed argument objects, non-ASCII punctuation in keys).
  - Empty tool call generation with refusal/clarification text despite `force_tools=True`.
  - Numeric sign errors (e.g., negative minutes/hours).
- Why `0ms` appears:
  - In `generate_cactus`, JSON decode failure falls back to `{function_calls: [], total_time_ms: 0, confidence: 0}`.
  - Source ref: `/Users/jaehong/Desktop/functiongemma-hackathon/main.py:32`

## 5) Cloud Fallback Availability and Comparison
- Availability probe:
  - `gemini-2.0-flash`: not available (404 for this account)
  - `gemini-2.5-flash-lite`: available
  - `gemini-2.5-flash`: available
- 30-case cloud-only snapshot (single pass):
  - `gemini-2.5-flash-lite`: avg F1 `0.9056`, avg latency `~783ms`
  - `gemini-2.5-flash`: avg F1 `0.9156`, avg latency `~1519ms`
- Interpretation:
  - Cloud improves correctness a lot vs current on-device route.
  - Accuracy is high but not guaranteed (strict argument/string matching still fails some cases).

## 6) Minimal Rule Set (Low Overfitting) for `generate_hybrid`
These rules are designed around failure types, not benchmark-specific phrases.

1. Output Integrity Gate
- If local output is structurally invalid, fallback to cloud.
- Conditions:
  - parse failure sentinel (`confidence == 0` and `total_time_ms == 0` and no calls)
  - any call missing `name` or non-dict `arguments`
  - predicted tool name not in provided tool set

2. Empty-Call Safety Gate
- If local returns no function call while tools exist, fallback to cloud.
- Especially when response text indicates refusal/clarification behavior.

3. Argument Sanity Gate
- Validate obvious schema-incompatible values before accepting local output.
- Generic checks:
  - required args present/non-empty
  - integer fields are integers
  - time-like numeric fields (`hour`, `minute`, `minutes`) are non-negative and in reasonable ranges
- On failure: fallback to cloud.

4. Multi-Action Risk Gate
- If user prompt likely requests multiple actions (e.g., conjunction signals), but local returns <2 calls, fallback to cloud.
- Keep this heuristic lightweight and language-agnostic (count simple conjunction markers).

5. Cost-Aware Cloud Routing
- Default cloud fallback model: `gemini-2.5-flash-lite` (latency advantage).
- Optional escalation to `gemini-2.5-flash` only for high-risk/critical retries.

## 7) Why This Rule Set (Generalization Rationale)
- Targets stable failure modes (`parse_fail`, `empty_calls`, malformed args, missing multi-calls).
- Avoids hardcoding benchmark-specific utterances.
- Preserves on-device wins when output is valid.
- Uses cloud only when local quality is likely unsafe.

## 8) Immediate Next Implementation Steps
1. Implement the 5-rule gate logic only inside `generate_hybrid` (keep signature unchanged).
2. Add env-driven cloud model selection:
   - `GEMINI_MODEL_FALLBACK=gemini-2.5-flash-lite` default.
3. Re-run:
   - `python /Users/jaehong/Desktop/functiongemma-hackathon/benchmark.py`
4. Compare before/after:
   - F1, avg time, on-device ratio, total score.

## 9) Repro Commands Used in This Session
- Run benchmark:
  - `python /Users/jaehong/Desktop/functiongemma-hackathon/benchmark.py`
- Ensure env in current shell:
  - `source ~/.zshrc`
  - `source /Users/jaehong/Desktop/functiongemma-hackathon/cactus/venv/bin/activate`
- Probe Gemini model availability:
  - tested with `google-genai` `client.models.generate_content(...)` on candidate model IDs.

## 10) Operational Notes
- Do not commit secrets from shell profiles (`GEMINI_API_KEY`, HF token).
- Because benchmark behavior is stochastic, evaluate strategies with multiple runs where possible.
