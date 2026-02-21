"""Debug script to see raw cactus output for failing cases."""
import sys
import json
sys.path.insert(0, "cactus/python/src")
from cactus import cactus_init, cactus_complete, cactus_destroy
from main import _LOCAL_SYSTEM_PROMPT, _enhance_tools, _prune_tools, _repair_json_payload
import benchmark

_FUNCTIONGEMMA_PATH = "cactus/weights/functiongemma-270m-it"

# Test a subset of failing cases
failing_cases = [
    "alarm_6am", "play_bohemian", "reminder_meeting", "search_bob", "weather_paris",
    "message_among_three", "alarm_among_three", "music_among_three",
    "timer_and_music", "alarm_and_weather",
]

for case in benchmark.BENCHMARKS:
    if case["name"] not in failing_cases:
        continue

    user_text = case["messages"][0]["content"]
    tools = case["tools"]
    enhanced = _enhance_tools(tools)
    pruned = _prune_tools(user_text, enhanced)

    print(f"\n{'='*60}")
    print(f"Case: {case['name']} | User: {user_text}")
    print(f"Tools available: {[t['name'] for t in tools]}")
    print(f"Pruned to: {[t['name'] for t in pruned]}")
    print(f"Expected: {case['expected_calls']}")

    model = cactus_init(_FUNCTIONGEMMA_PATH)
    cactus_tools = [{"type": "function", "function": t} for t in pruned]

    raw_str = cactus_complete(
        model,
        [{"role": "system", "content": _LOCAL_SYSTEM_PROMPT}] + case["messages"],
        tools=cactus_tools,
        force_tools=True,
        max_tokens=512,
        temperature=0.2,
        confidence_threshold=0.0,
        tool_rag_top_k=0,
        stop_sequences=["<end_of_turn>"],
    )
    cactus_destroy(model)

    print(f"Raw output: {raw_str[:500]}")

    try:
        parsed = json.loads(raw_str)
        print(f"Parsed: {json.dumps(parsed, indent=2)[:300]}")
    except:
        try:
            repaired = _repair_json_payload(raw_str)
            parsed = json.loads(repaired)
            print(f"Repaired+Parsed: {json.dumps(parsed, indent=2)[:300]}")
        except:
            print(f"PARSE FAILED even after repair")
