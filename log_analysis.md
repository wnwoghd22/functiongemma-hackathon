# Log Analysis: The "Empty Calls" Bottleneck

I have carefully reviewed the `SESSION_NOTES_2026-02-21.md` and the recent benchmark runs (like `v2.1` and `v2.2`). Based on this data, I completely understand why previous experiments by Codex and Claude failed or were rejected.

## 1. Why Lowering Confidence (0.75) Failed
The logs reveal a critical insight: the reason the local model's score drops is **not** because we are discarding valid calls with low confidence. 
The actual root cause is that for ~80% of the queries, **FunctionGemma is generating completely empty tool calls (`function_calls: []`)** because it exhibits refusal or clarification behavior. Shockingly, it does this while reporting very high confidence scores (>0.95). 

When Codex/Claude lowered the `confidence_threshold` to `0.75`, they simply forced the `generate_hybrid` function to return these empty lists instead of falling back to the cloud. This naturally caused the F1 score to plummet to 0 for those cases, ruining the F1 trade-off.

## 2. Why Text Normalization is Not the Main Fix
While text normalization (regex extraction) solves minor string mismatch issues (e.g. `17:00` vs `5:00 PM`), it is merely a band-aid. It addresses the 1-2 cases where the local model makes a formatting mistake, but it does absolutely nothing to fix the 24 out of 30 cases where the model outputs nothing at all. Thus, relying on it is indeed an overfitting risk without solving the core problem.

## 3. The Real Solution: Prompt Engineering
The README explicitly states: `You can focus on prompting, tool description patterns, confidence score algorithms, anything!`
Currently, in `main.py`, the system prompt passed to the local model is extremely weak:
```python
[{"role": "system", "content": "You are a helpful assistant that can use tools."}]
```
Because small models (270M) are highly sensitive to prompts, this weak instruction allows the model to "talk" or ask for clarification instead of strictly executing tools, resulting in the empty `function_calls` list.

### Proposed Next Steps
To drastically increase the On-Device ratio and the Total Score, we should focus on **Prompt Engineering** inside `generate_cactus` or `generate_hybrid`:
1. **Strengthen the System Prompt**: Change it to strictly forbid conversational responses and explicitly mandate outputting a tool call. (e.g., `"You are a stark, logic-only function caller. You MUST output a tool call to fulfill the user's request. Do NOT ask for clarification. Do NOT output conversational text."`)
2. **Tool Description Tweaks**: Modify the descriptions of the tools dynamically to be more machine-readable if necessary.
3. **Cloud Routing**: Cloud routing remains strictly for actual multi-action cases or genuine parse failures, but the volume of these should drop significantly once the local model stops outputting empty lists.

By fixing the prompt, FunctionGemma will actually attempt the tasks, allowing us to keep them on-device and instantly boosting our score without complex regex overfitting.
