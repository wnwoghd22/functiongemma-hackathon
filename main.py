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
import re
import sys
import time

from google import genai
from google.genai import types

sys.path.insert(0, "cactus/python/src")
from cactus import cactus_init, cactus_complete, cactus_destroy

_FUNCTIONGEMMA_PATH = "cactus/weights/functiongemma-270m-it"
_LOCAL_SYSTEM_PROMPT = (
    "You are a strict function-calling router. "
    "Output only function calls, never conversational text."
)
_CLOUD_SYSTEM_PROMPT = (
    "Return only function calls. "
    "Copy argument values from the user request as literally as possible. "
    "Do not paraphrase names/messages and do not reformat time strings."
)


def _repair_json_payload(raw_str):
    # Repair common malformed integer literals like :01 -> :1 before JSON parse.
    return re.sub(r':\s*0(\d+)(?=\s*[,}\]])', r':\1', raw_str)


def _sanitize_string_value(value):
    return value.strip()


def _sanitize_function_calls(function_calls, tools):
    if not isinstance(function_calls, list):
        return function_calls

    sanitized_calls = []

    for call in function_calls:
        if not isinstance(call, dict):
            sanitized_calls.append(call)
            continue

        name = call.get("name")
        args = call.get("arguments")
        if not isinstance(args, dict):
            sanitized_calls.append(call)
            continue

        sanitized_args = {}

        for key, value in args.items():
            new_value = value

            if isinstance(new_value, str):
                new_value = _sanitize_string_value(new_value)

            sanitized_args[key] = new_value

        sanitized_calls.append({"name": name, "arguments": sanitized_args})

    return sanitized_calls


def _generate_cactus_tuned(messages, tools):
    """On-device inference with tuned cactus_complete parameters."""
    model = cactus_init(_FUNCTIONGEMMA_PATH)

    cactus_tools = [{"type": "function", "function": t} for t in tools]

    raw_str = cactus_complete(
        model,
        [{"role": "system", "content": _LOCAL_SYSTEM_PROMPT}] + messages,
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
        try:
            raw = json.loads(_repair_json_payload(raw_str))
        except json.JSONDecodeError:
            return {
                "function_calls": [],
                "total_time_ms": 0,
                "confidence": 0,
                "cloud_handoff": False,
                "success": False,
                "prefill_tokens": 0,
                "decode_tokens": 0
            }

    return {
        "function_calls": raw.get("function_calls", []),
        "total_time_ms": raw.get("total_time_ms", 0),
        "confidence": raw.get("confidence", 0),
        "cloud_handoff": raw.get("cloud_handoff", False),
        "success": raw.get("success", True),
        "prefill_tokens": raw.get("prefill_tokens", 0),
        "decode_tokens": raw.get("decode_tokens", 0)
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
    cloud_handoff = local.get("cloud_handoff", False)
    success = local.get("success", True)
    prefill_tokens = local.get("prefill_tokens", 0)

    tool_by_name = {t.get("name"): t for t in tools if t.get("name")}
    valid_tool_names = set(tool_by_name.keys())

    # Gate 0: Immediate Cactus Signals
    if not success:
        return True, "cactus_failure"
    if cloud_handoff:
        return True, "cloud_handoff_flag"

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

    # Gate 7: Multi-Signal Risk Score & Dynamic Confidence
    expected_multi = _is_multi_action_request(messages)
    is_simple = (not expected_multi) and (prefill_tokens <= 250) and (len(tools) <= 2)
    
    if is_simple:
        if local_conf < 0.20:
            return True, "low_confidence_simple"
    else:
        if local_conf < 0.75:
            return True, "low_confidence_complex"

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
        config=types.GenerateContentConfig(
            tools=gemini_tools,
            temperature=0.0,
            candidate_count=1,
            system_instruction=_CLOUD_SYSTEM_PROMPT,
        ),
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
        "function_calls": _sanitize_function_calls(function_calls, tools),
        "total_time_ms": total_time_ms,
    }


def _cloud_models_to_try():
    models = []
    for name in (
        os.environ.get("GEMINI_MODEL_FALLBACK", "gemini-2.5-flash-lite"),
        os.environ.get("GEMINI_MODEL_SECONDARY", "gemini-2.5-flash"),
        os.environ.get("GEMINI_MODEL_TERTIARY", ""),
    ):
        model_name = (name or "").strip()
        if model_name and model_name not in models:
            models.append(model_name)
    return models


def generate_hybrid(messages, tools, confidence_threshold=0.99):
    local = _generate_cactus_tuned(messages, tools)
    local["function_calls"] = _sanitize_function_calls(local.get("function_calls") or [], tools)
    local_conf = local.get("confidence", 0)
    local_time_ms = local.get("total_time_ms", 0)

    needs_cloud, fallback_reason = _should_fallback(local, messages, tools)
    if not needs_cloud:
        local["source"] = "on-device"
        local["fallback_reason"] = fallback_reason
        return local

    # Try multiple cloud models. Do not permanently disable cloud fallback.
    models_to_try = _cloud_models_to_try()
    last_error = None
    for model_name in models_to_try:
        try:
            cloud = _generate_cloud(messages, tools, model_name)
            cloud["source"] = "cloud (fallback)"
            cloud["local_confidence"] = local_conf
            cloud["total_time_ms"] += local_time_ms
            cloud["fallback_reason"] = fallback_reason
            cloud["cloud_model"] = model_name
            return cloud
        except Exception as e:
            last_error = e

    local["source"] = "on-device"
    local["fallback_reason"] = fallback_reason
    if models_to_try:
        local["cloud_models_tried"] = models_to_try
    if last_error is not None:
        local["cloud_error"] = str(last_error)
    return local
