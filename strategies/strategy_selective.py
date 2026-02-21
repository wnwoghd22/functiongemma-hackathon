"""Selective routing strategy v2.2: cactus_complete parameter tuning for on-device ratio.

v2.1: F1=0.96, on-device=20%, score=60.9%

v2.2 changes:
- Direct cactus_complete call with tuned parameters:
  - confidence_threshold=0.0 (prevent early cloud_handoff on first-token uncertainty)
  - temperature=0.2 (escape greedy decoding refusal traps)
  - tool_rag_top_k=0 (disable tool filtering, include all tools in prompt)
  - max_tokens=512 (more token space for multi-call attempts)
  - Remove <|im_end|> stop sequence (unnecessary for Gemma)
- Routing gates unchanged from v2.1.
- Target: on-device 25-35%, F1 maintained.
"""

import json
import os
import sys
import time

from google import genai
from google.genai import types

sys.path.insert(0, "cactus/python/src")
from cactus import cactus_init, cactus_complete, cactus_destroy

_FUNCTIONGEMMA_PATH = "cactus/weights/functiongemma-270m-it"


def _generate_cactus_tuned(messages, tools):
    """On-device inference with tuned cactus_complete parameters."""
    model = cactus_init(_FUNCTIONGEMMA_PATH)

    cactus_tools = [{"type": "function", "function": t} for t in tools]

    raw_str = cactus_complete(
        model,
        [{"role": "system", "content": "You are a helpful assistant that can use tools."}] + messages,
        tools=cactus_tools,
        force_tools=True,
        max_tokens=512,
        temperature=0.2,
        confidence_threshold=0.0,
        tool_rag_top_k=0,
        stop_sequences=["<end_of_turn>"],
    )

    cactus_destroy(model)

    try:
        raw = json.loads(raw_str)
    except json.JSONDecodeError:
        return {
            "function_calls": [],
            "total_time_ms": 0,
            "confidence": 0,
        }

    return {
        "function_calls": raw.get("function_calls", []),
        "total_time_ms": raw.get("total_time_ms", 0),
        "confidence": raw.get("confidence", 0),
    }


def _is_multi_action_request(messages):
    user_text = " ".join(
        str(m.get("content", ""))
        for m in messages
        if m.get("role") == "user"
    ).lower()
    markers = (" and ", " then ", " also ", " plus ", ", and ", " 그리고 ", " 및 ")
    return any(marker in user_text for marker in markers) or user_text.count(",") >= 2


def _should_fallback(local, messages, tools):
    local_calls = local.get("function_calls") or []
    local_conf = local.get("confidence", 0)
    local_time_ms = local.get("total_time_ms", 0)

    tool_by_name = {t.get("name"): t for t in tools if t.get("name")}
    valid_tool_names = set(tool_by_name.keys())

    # Gate 1: Parse failure sentinel — hard failure, must fallback.
    if local_conf == 0 and local_time_ms == 0 and not local_calls:
        return True, "parse_fail_sentinel"

    # Gate 2: Structural integrity — malformed calls.
    for call in local_calls:
        if not isinstance(call, dict):
            return True, "invalid_call_shape"
        if not isinstance(call.get("name"), str):
            return True, "invalid_call_name"
        if not isinstance(call.get("arguments"), dict):
            return True, "invalid_call_arguments"
        if valid_tool_names and call["name"] not in valid_tool_names:
            return True, "unknown_tool_name"

    # Gate 3: Empty calls — tools are available but local returned nothing.
    # Local model often returns empty calls with high confidence (refusal behavior).
    # Always fallback since an empty response is never correct when tools exist.
    if tools and not local_calls:
        return True, "empty_function_calls"

    # Gate 4: Required argument missing — hard schema violation.
    for call in local_calls:
        schema = tool_by_name.get(call["name"], {}).get("parameters", {})
        required = schema.get("required", [])
        args = call.get("arguments", {})
        for req_key in required:
            if req_key not in args:
                return True, "missing_required_argument"
            value = args.get(req_key)
            if value is None:
                return True, "null_required_argument"
            if isinstance(value, str) and not value.strip():
                return True, "empty_required_string"

    # Gate 5: Time-field sanity — only obviously wrong values.
    for call in local_calls:
        schema = tool_by_name.get(call["name"], {}).get("parameters", {})
        properties = schema.get("properties", {})
        args = call.get("arguments", {})
        for key, prop in properties.items():
            if key not in args:
                continue
            value = args[key]
            prop_type = str(prop.get("type", "")).lower()
            if prop_type == "integer" and isinstance(value, (int, float)) and not isinstance(value, bool):
                v = int(value) if isinstance(value, float) and value.is_integer() else value
                if isinstance(v, int):
                    if key == "hour" and not (0 <= v <= 23):
                        return True, "hour_out_of_range"
                    if key == "minute" and not (0 <= v <= 59):
                        return True, "minute_out_of_range"
                    if key in ("minutes", "seconds", "duration") and v < 0:
                        return True, "negative_time_value"

    # Gate 6: Multi-action under-call — local almost never gets multi-action right.
    if _is_multi_action_request(messages) and len(local_calls) < 2:
        return True, "multi_action_under_called"

    # Gate 7: Tool-count gate — when many tools are available, local often picks
    # the wrong one. Medium cases (*_among_*) typically have 3+ tools.
    if len(tools) >= 3 and local_conf < 0.75:
        return True, "many_tools_low_conf"

    # Gate 8: Moderate confidence gate — even with 1-2 tools, very low confidence
    # means local is likely semantically wrong despite valid structure.
    if local_conf < 0.6:
        return True, "low_confidence"

    # No fallback: keep on-device.
    return False, "on_device_ok"


def _generate_cloud(messages, tools, model_name):
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
    gemini_tools = [
        types.Tool(function_declarations=[
            types.FunctionDeclaration(
                name=t["name"],
                description=t["description"],
                parameters=types.Schema(
                    type="OBJECT",
                    properties={
                        k: types.Schema(type=v["type"].upper(), description=v.get("description", ""))
                        for k, v in t["parameters"]["properties"].items()
                    },
                    required=t["parameters"].get("required", []),
                ),
            )
            for t in tools
        ])
    ]

    contents = [m["content"] for m in messages if m["role"] == "user"]
    start_time = time.time()
    gemini_response = client.models.generate_content(
        model=model_name,
        contents=contents,
        config=types.GenerateContentConfig(tools=gemini_tools),
    )
    total_time_ms = (time.time() - start_time) * 1000

    function_calls = []
    for candidate in (gemini_response.candidates or []):
        content = getattr(candidate, "content", None)
        if not content or not getattr(content, "parts", None):
            continue
        for part in content.parts:
            if part.function_call:
                function_calls.append({
                    "name": part.function_call.name,
                    "arguments": dict(part.function_call.args) if part.function_call.args else {},
                })

    return {
        "function_calls": function_calls,
        "total_time_ms": total_time_ms,
    }


def generate_hybrid(messages, tools, confidence_threshold=0.99):
    local = _generate_cactus_tuned(messages, tools)
    local_conf = local.get("confidence", 0)
    local_time_ms = local.get("total_time_ms", 0)

    if getattr(generate_hybrid, "_disable_cloud_fallback", False):
        local["source"] = "on-device"
        return local

    needs_cloud, fallback_reason = _should_fallback(local, messages, tools)
    if not needs_cloud:
        local["source"] = "on-device"
        local["fallback_reason"] = fallback_reason
        return local

    # Single cloud model — gemini-2.5-flash-lite for speed.
    fallback_model = os.environ.get("GEMINI_MODEL_FALLBACK", "gemini-2.5-flash-lite")
    try:
        cloud = _generate_cloud(messages, tools, fallback_model)
        cloud["source"] = "cloud (fallback)"
        cloud["local_confidence"] = local_conf
        cloud["total_time_ms"] += local_time_ms
        cloud["fallback_reason"] = fallback_reason
        cloud["cloud_model"] = fallback_model
        return cloud
    except Exception as e:
        generate_hybrid._disable_cloud_fallback = True
        local["source"] = "on-device"
        local["fallback_reason"] = fallback_reason
        local["cloud_error"] = str(e)
        return local
