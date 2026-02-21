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

## 11) Experiment Update: Minimal 5-Rule Routing
- Implemented in:
  - `/Users/jaehong/Desktop/functiongemma-hackathon/main.py` (`generate_hybrid` only)
- Added rule gates:
  - Output integrity
  - Empty-call safety
  - Argument sanity
  - Multi-action under-calling
  - Cost-aware cloud model routing (`gemini-2.5-flash-lite` default, `gemini-2.5-flash` escalation)
- Benchmark result after rule insert (single run):
  - overall avg F1: `0.94` (up from ~`0.24`)
  - avg time: `1248ms` (up from ~`394ms`)
  - on-device ratio: `20%` (down from `100%`)
  - total score: `59.9%` (up from ~`40.0%`)
- Interpretation:
  - The rules strongly improved correctness by aggressively recovering local failure modes with cloud fallback.
  - Latency and on-device ratio worsened, so next iteration should reduce unnecessary cloud routing on medium/hard cases where local is still usable.

## 12) Why Score Increased (Rule Attribution)
- Detailed comparison snapshot:
  - local total score: `43.12`
  - 5-rule hybrid total score: `59.95`
  - local avg F1: `0.30` -> hybrid avg F1: `0.9444`
  - local avg time: `413.6ms` -> hybrid avg time: `1325.46ms`
  - hybrid on-device ratio: `20%`
- Fallback reason counts (hybrid run):
  - `empty_function_calls`: 14
  - `parse_fail_sentinel`: 5
  - `multi_action_under_called`: 3
  - `low_confidence`: 1
  - `hour_out_of_range`: 1
- Main contributor:
  - Most gains came from converting prior `F1=0` local failures (`parse_fail` and `empty calls`) into cloud-correct calls.

## 13) Why F1 Looks Near-Discrete (Mostly 0/1)
- This is expected with current benchmark composition and matching rules:
  - Expected-call count distribution:
    - 1 call: 20 cases
    - 2 calls: 7 cases
    - 3 calls: 3 cases
- Matching strictness:
  - function name must match exactly
  - required argument keys must exist
  - argument values must match after only `strip().lower()` normalization
  - punctuation/details can still fail equality checks
- Therefore:
  - single-call cases naturally collapse to mostly `0` or `1`
  - partial values like `0.67` mainly appear in multi-call cases (e.g., 1/2 matched)
  - parse failures often become immediate `0` because local fallback object has empty calls

## 14) Full On-Device vs Full-Cloud Comparison (Feature Extraction)
- Re-measured with:
  - full on-device: `generate_cactus` only
  - full cloud: `gemini-2.5-flash-lite` only
- Global snapshot:
  - local avg F1: `0.2444`
  - cloud avg F1: `0.9111`
  - local avg time: `403.98ms`
  - cloud avg time: `1178.02ms`
  - local score-like: `39.99`
  - cloud score-like: `55.0`

### Cross-outcome counts
- both correct: `6`
- local-only correct: `0`
- cloud-only correct: `20`
- both not perfect: `4`

### Traits of on-device strong tasks
- On-device perfect cases were all `single-action` (`expected_calls=1`).
- On-device perfect cases were all `multi_action=False`.
- Typical successful signatures:
  - `('get_weather',)` (some cases)
  - `('play_music',)`
  - `('set_timer',)` / `('set_alarm',)` in limited settings
- For multi-call tasks (`expected_calls >= 2`), on-device perfect rate was effectively `0.00`.

### Traits of cloud-gain tasks
- Biggest gains concentrated in:
  - `multi_action=True`
  - `expected_calls=2 or 3`
  - signatures including `send_message`, `search_contacts`, `create_reminder`
- Cloud still not guaranteed perfect due to strict string/value matching (e.g., punctuation or phrasing differences).

### Aggregated feature view (perfect-rate)
- by `multi_action`:
  - local: `False=0.30`, `True=0.00`
  - cloud: `False=0.90`, `True=0.80`
- by `n_expected_calls`:
  - local: `1=0.30`, `2=0.00`, `3=0.00`
  - cloud: `1=0.90`, `2=0.86`, `3=0.67`

### Strategic implication
- Routing should avoid one-size-fits-all:
  - keep clearly single/simple cases on-device
  - escalate multi-action and communication-heavy tasks to cloud
- This split is more robust than case-specific hardcoding and aligns with hidden-eval generalization goals.

## 15) Low-Level Scope Clarification (What Is Actually In-Bounds)
- In-bounds for hackathon scoring:
  - Internal logic of `generate_hybrid` in `main.py`
  - Prompting/options passed to `cactus_complete`
  - Routing policy, validation gates, retry/escalation, output post-processing
- Out-of-bounds or low-impact for leaderboard scoring:
  - Changing local benchmark scoring logic (`benchmark.py`) does not transfer to server score.
  - C++ engine/source tuning is not part of submission payload for leaderboard eval.
- Why:
  - README says primary task is internal logic of `generate_hybrid`.
  - `submit.py` uploads `main.py` file to eval server.
  - Local `benchmark.py` is for iteration only and can diverge from server-side evaluator.
- Source refs:
  - `/Users/jaehong/Desktop/functiongemma-hackathon/README.md:34`
  - `/Users/jaehong/Desktop/functiongemma-hackathon/README.md:35`
  - `/Users/jaehong/Desktop/functiongemma-hackathon/submit.py:22`
  - `/Users/jaehong/Desktop/functiongemma-hackathon/submit.py:26`

## 16) Multi-Tool Partial Routing Feasibility
- Question: for a multi-action task, can some tools be on-device and others via cloud?
- Short answer: yes, in user-space orchestration inside `generate_hybrid`.
- Mechanically possible because benchmark only scores returned `function_calls` list, not generation provenance.
- Practical pattern:
  1. Run local once.
  2. Validate local calls (structure/name/args/coverage).
  3. If multi-action is under-called or low-confidence, run cloud for recovery.
  4. Merge/dedupe calls and return one final list.
- Constraints and risks:
  - Duplicate calls can lower precision.
  - Conflicting arguments across local/cloud need deterministic tie-break rules.
  - Latency increases if both paths are always run.
  - Overfitting risk if merge logic is benchmark-case specific.
- Related implementation cues:
  - Current code already has fallback gates and cloud retry points.
  - Multi-action detection exists and can trigger selective second-pass calls.
- Source refs:
  - `/Users/jaehong/Desktop/functiongemma-hackathon/main.py:97`
  - `/Users/jaehong/Desktop/functiongemma-hackathon/main.py:179`
  - `/Users/jaehong/Desktop/functiongemma-hackathon/benchmark.py:471`
  - `/Users/jaehong/Desktop/functiongemma-hackathon/benchmark.py:472`

## 17) Benchmark Update: 20260222_020138 (v2.2 + fuzzy)
- New run file:
  - `/Users/jaehong/Desktop/functiongemma-hackathon/benchmark_runs/benchmark_20260222_020138.md`
- Reported metrics:
  - total score: `62.5%`
  - avg F1: `0.97`
  - avg time: `957.72ms`
  - on-device ratio: `20%`
- Relative snapshots:
  - `v2.1 (013032)`: `60.9%`, F1 `0.96`, on-device `20%`
  - `v2.2 strict (014541)`: `59.2%`, F1 `0.92`, on-device `20%`
  - `v21_minplus (015239)`: `60.2%`, F1 `0.96`, on-device `20%`

## 18) Interpreting the 62.5% Rise (Important Caveat)
- The `020138` note explicitly states this run used fuzzy matching changes in `benchmark.py`
  (`_normalize()` and `_time_equivalent()` enhancements).
- This can raise local score without changing routing quality.
- Since leaderboard submission sends `main.py`, benchmark-side normalization changes are unlikely to affect official hidden-eval results.
- Therefore:
  - treat `62.5%` as local-analysis signal, not guaranteed leaderboard gain.
  - keep routing improvements and optional output normalization in `main.py`, not in benchmark scorer.
- Source refs:
  - `/Users/jaehong/Desktop/functiongemma-hackathon/benchmark_runs/benchmark_20260222_020138.md:88`
  - `/Users/jaehong/Desktop/functiongemma-hackathon/benchmark_runs/benchmark_20260222_020138.md:84`
  - `/Users/jaehong/Desktop/functiongemma-hackathon/submit.py:22`

## 19) Fuzzy Matching vs Multi-Action (Relation and Co-Use)
- They are related but solve different failure classes:
  - Multi-action routing addresses missing/under-called function sets (coverage problem).
  - Fuzzy normalization addresses lexical/value drift in arguments (matching problem).
- Why they often co-occur:
  - Multi-action cases contain more argument fields across more calls, so one lexical mismatch can sink F1.
- Can they be used together?
  - Yes, and this is recommended.
  - Use routing to get the right set/number of calls.
  - Use lightweight canonicalization in `main.py` output post-processing for high-variance fields
    (for example message punctuation/case and time-format normalization).
- Guardrails:
  - keep canonicalization conservative and schema-aware.
  - avoid broad fuzzy rewrites that can hide genuinely wrong semantics.
  - avoid benchmark-only scorer edits when evaluating leaderboard readiness.

## 20) Practical Next Experiment Direction
- Base strategy: keep `v2.1` routing backbone (stronger hard-task stability than minplus in recent runs).
- Add minimal post-processing in `main.py` only:
  1. canonicalize `send_message.message` punctuation/case normalization
  2. canonicalize time formats (`5:00 PM` vs `17:00`) for reminder/alarm-like arguments
  3. no semantic rewriting of content words
- Then run A/B:
  - local benchmark with current scorer
  - submit one hourly leaderboard trial to validate transferability.
