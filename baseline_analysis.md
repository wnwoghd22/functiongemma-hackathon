# FunctionGemma Hybrid Routing - Baseline Analysis

## Overview
The goal is to optimize the `generate_hybrid` routing algorithm in `main.py` for the Cactus DeepMind Hacker challenge to achieve a score of over 60 points. 

The benchmark (`benchmark.py`) evaluates three main metrics:
1. **F1 Score (50%)**: Accuracy of the predicted tool calls compared to expected.
2. **Time Score (25%)**: Generation latency (anything under 500ms gets full marks).
3. **On-Device Ratio (25%)**: The percentage of requests handled locally by FunctionGemma vs. falling back to the cloud (Gemini-2.5-Flash).

### Baseline Results
Running the initial `benchmark.py` yields the following performance metrics:
- **Total Score**: ~61.5%
- **Overall F1 Score**: 0.96
- **Average Time**: ~1045ms
- **On-Device Ratio**: 20% (6/30 local, 24/30 cloud)

## Identifying the Bottlenecks

The current F1 score is quite high, but the overall score is dragged down by the high latency and low on-device ratio. Both of these issues stem from **overly aggressive cloud fallbacks**.

### 1. The Confidence Threshold is Too High
In `main.py`, the default `confidence_threshold` is set to `0.99`. This means any local prediction with a confidence score under 99% is automatically delegated to the cloud.
- **Impact**: This forces 80% of queries to fall back to the slower Cloud model, hurting both the *Time Score* and the *On-Device Ratio*.
- **Observation**: Many local outputs that are perfectly valid or structurally sound are penalized simply for having a confidence score like `0.95`.

### 2. Strict Error Catching Without Correction
The current `generate_hybrid` function has strict validation gates (checking schema, ranges, etc.). If the local model makes a minor formatting mistake (e.g., missing capitalization or omitting a secondary argument like minutes), the algorithm simply throws it to the cloud.
- **Impact**: We waste the local model's execution time, then incur the penalty of a cloud API request time. 
- **Observation**: For tools like `send_message`, the local model often accurately predicts the *need* for the tool but slightly messes up the exact string. These could be locally corrected by extracting context from the user string.

## Proposed Strategy

To significantly exceed the 60-point threshold, the routing strategy must be tuned to prioritize local generation and execute fast local corrections:

1. **Lower the Confidence Threshold**: Reduce the default threshold (e.g., to `0.80`). If the local model's output passes all structural and schema-validation gates, we should trust it, even if confidence isn't 99%.

2. **Local Text-Normalization (Heuristic Correction)**:
   - For tools like `send_message` or `set_alarm`, implement regex-based extraction to pull the recipient name, message text, or time directly from the user's prompt. 
   - If the local model hallucinates or drops a small argument, fix the dictionary programmatically *before* deciding to fall back to the cloud.

3. **Refine the Fallback Logic**:
   - Only fall back to the cloud if the request is explicitly *multi-action* (detected via keywords like "and", "then") but the local model only returned a single call.
   - Use cloud fallback sparingly for true zero-confidence or complete parsing failures.

By keeping more structurally sound queries on-device and applying fast python-based corrections, we can drastically reduce average latency and increase the on-device ratio while maintaining a high F1 score.
