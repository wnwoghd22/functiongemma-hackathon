# Hybrid Routing Strategy (Next Generation)

## Background & Paradigm Shift

Through baseline analysis and several benchmark runs, we discovered a core truth about the scoring mechanism and the local model's behavior:
1. **The Cloud Trap**: Because `benchmark.py` heavily rewards generation time < 500ms and On-Device usage, relying too much on cloud fallback (even if F1 is perfect) aggressively caps the score around 60%.
2. **The "Empty Call" Bottleneck**: Lowering the `confidence_threshold` to keep more requests on-device previously failed because `FunctionGemma` was actively refusing to use tools (returning empty dictionaries) when presented with a conversational user text.

To break the 60% barrier, we tried removing all hardcoded parameter extractions (which are vulnerable to overfitting hidden test cases) and applied **Strict Prompt Engineering** instead. 

**Result**: The On-Device ratio naturally jumped from **20% to 27%**, with a benchmark score of **59.7%** without any overfitting heuristics.

## The New Strategy: Prompt Engineering + Multi-Signal Routing

To reach the 80%+ threshold, we must combine our successful prompt engineering with a more intelligent routing mechanism that looks beyond a single `confidence` score.

### 1. Maintain Strict Prompt Engineering
As tested, changing the system prompt from `"You are a helpful assistant..."` to a strict negative-constraint prompt (`"You are a strict, logic-only function routing engine. NEVER ask for clarification..."`) forces the model to attempt tool calls instead of conversational refusal. This remains our foundation.

### 2. Multi-Signal Risk Score (The New Fallback Logic)
Relying solely on `confidence < 0.99` throws away too many perfectly valid on-device calls. We will calculate a **Risk Score** based on multiple local metrics:

*   **`cloud_handoff` flag**: This is a direct signal from `cactus_complete`. If the local model internally flags that it needs the cloud, we should trust it and fall back.
*   **`success` flag**: If `cactus_complete` reports `success=False` (e.g. token limit hit, early termination), we must fall back.
*   **Token Metrics (`prefill_tokens`, `decode_tokens`)**: 
    *   If `prefill_tokens` is extremely high (long, complex user prompt with many tools), the risk of multi-action failure increases.
    *   If `decode_tokens` is very short despite tools being available, it's a strong indicator of an under-call or empty call.
*   **Tool Count vs. Action Expectation**: By searching the user prompt for words like "and", "then", or commas, we can estimate if it's a multi-action request. If we expect multi-action but the local model only generated one call, increase the risk score.
*   **Structural Validity**: (Already in `v2.2`) If arguments are missing, wrong types, or tool names are hallucinated, the risk score is maximum (immediate fallback).

### 3. Dynamic Thresholding
Instead of a static `confidence_threshold`, we will dynamically adjust the required confidence based on the Risk Score. 
*   If the request is simple (1 expected action, short prefill, `cloud_handoff=False`), we accept the local output even if `confidence` is as low as `0.50`.
*   If the request is complex or ambiguous, we demand a much higher confidence (e.g., `0.95`) or route to the cloud entirely.

## Next Steps for Implementation
1. Ensure `generate_cactus` extracts and returns the extended fields: `cloud_handoff`, `success`, `prefill_tokens`, `decode_tokens`.
2. Rewrite `_should_fallback` in `main.py` to calculate the mathematical Risk Score instead of sequential `if` constraints.
3. Validate against the local benchmark and review the generated logs in `benchmark_runs/`.
