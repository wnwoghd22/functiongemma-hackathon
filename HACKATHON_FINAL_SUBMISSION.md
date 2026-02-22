# Cactus x Google DeepMind Hackathon - Final Submission

## Team
- Team name: `jay`
- Location: `Online`

## What We Built
We built a hybrid function-calling router around FunctionGemma (on-device) with optional Gemini cloud fallback logic inside `main.py`.

The core objective was to maximize total score under the hackathon metric by balancing:
- tool-call correctness (F1),
- end-to-end latency,
- on-device ratio.

## Working Demo
The solution is runnable in this repository with:

```bash
python benchmark.py
```

This demonstrates end-to-end tool-call generation and scoring for easy/medium/hard tasks.

For leaderboard evaluation, we submit:

```bash
python submit.py --team "jay" --location "Online"
```

## System Design and Routing Strategy
Our approach focused on reliability-first routing:

1. **On-device first path (FunctionGemma via Cactus)**
   - Local function-call generation for all requests.
   - Argument extraction and sanitization to reduce malformed outputs.
   - Multi-action handling for compound intents.

2. **Fast-path for clear single-intent requests**
   - Deterministic handling for unambiguous patterns to reduce latency.
   - Guarded by required-argument checks to avoid unsafe shortcuts.

3. **Fallback safety logic**
   - Structural checks for missing/invalid calls.
   - Recovery behavior when local output quality is weak.
   - Cloud fallback hooks are implemented, but final competitive runs prioritized stable on-device behavior.

## Why FunctionGemma + Gemini (Usage Rationale)
We intentionally optimized around FunctionGemma as the primary engine because the scoring formula rewards on-device execution and predictable latency/cost.

Gemini cloud fallback was implemented as a quality recovery path, but in official leaderboard outcomes our submissions repeatedly showed `on_device_pct=100%`. Because cloud materialization was not consistently observable in final scoring results, we shifted strategy toward robust local correctness instead of aggressive cloud dependence.

## Results
Best verified hidden-eval result:
- **Score:** `81.3`
- **F1:** `0.9389`
- **On-device:** `100.0%`
- **Avg Time:** `6911.7 ms`

(Recorded in `submission_results_summary_20260222.md` and reflected on leaderboard snapshot during the event.)

## Key Engineering Tradeoffs
- We favored **downside protection** over risky overfitting to a few public benchmark patterns.
- Fast-path was useful for latency upside, but only when strict validity guards were applied.
- For multi-intent requests, correctness stability mattered more than raw speed.

## Repository Pointers
- Main submission file: `main.py`
- Local benchmark: `benchmark.py`
- Submission client: `submit.py`
- Session log and benchmark deltas: `SESSION_NOTES_2026-02-21.md`
