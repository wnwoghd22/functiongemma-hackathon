# Routing Signal Guide (Beyond Confidence)

This note summarizes which signals can be used in `generate_hybrid` besides `confidence`,
and how to combine them without overfitting.

## Why This Matters

Relying on a single confidence threshold repeatedly caused trade-off collapse:
- keep too many requests on-device -> F1 drops
- fallback too aggressively -> on-device ratio drops

A multi-signal risk score is more stable than one threshold.

## Available Signals From Cactus Output

`cactus_complete` response includes:
- `cloud_handoff`
- `success`
- `function_calls`
- `confidence`
- `time_to_first_token_ms`
- `total_time_ms`
- `prefill_tps`
- `decode_tps`
- `prefill_tokens`
- `decode_tokens`
- `total_tokens`

Current `main.py` only returns:
- `function_calls`
- `total_time_ms`
- `confidence`

Source:
- `/Users/jaehong/Desktop/functiongemma-hackathon/main.py:41`
- `/Users/jaehong/Desktop/functiongemma-hackathon/main.py:45`
- `/Users/jaehong/Desktop/functiongemma-hackathon/README.md:117`

## Practical Signals To Add First

1. `cloud_handoff` and `success`
- High-value direct risk flags from local generation.
- If `cloud_handoff=true`, fallback is usually justified.

2. `prefill_tokens`
- Proxy for prompt complexity (long user text + many tools).
- Useful for predicting multi-tool error risk.

3. `decode_tokens`
- Very short decode often correlates with empty/under-called outputs.
- Good as an early failure signal with tools enabled.

4. Structural quality signals from `function_calls`
- call count vs. multi-action expectation
- unknown tool names
- required argument coverage
- type/range validity

5. Request-side complexity features
- `len(tools)`
- multi-action markers (`and`, `then`, commas, etc.)

## Suggested Risk Score Pattern

Use a weighted rule score instead of one threshold:

```text
risk =
  w1 * I(cloud_handoff) +
  w2 * I(not success) +
  w3 * I(multi_action and call_count < expected_min) +
  w4 * I(tool_count >= 3 and prefill_tokens > T1) +
  w5 * I(decode_tokens < T2) +
  w6 * schema_violation_count +
  w7 * max(0, conf_floor - confidence)
```

Decision:
- fallback to cloud if `risk >= R`
- otherwise keep on-device

This is easier to tune and more robust than `confidence < x` alone.

## Guardrails (Avoid Overfitting)

- Do not use case names or exact benchmark phrases.
- Prefer feature-level rules (tool count, call coverage, schema validity).
- Keep normalization conservative and schema-aware.
- Do not depend on local scorer changes in `benchmark.py` for leaderboard strategy.

## Recommended Next Implementation Step

In `main.py`, update `generate_cactus` to preserve additional Cactus fields
(`cloud_handoff`, `success`, token/tps metrics), then tune routing gates with A/B runs.

