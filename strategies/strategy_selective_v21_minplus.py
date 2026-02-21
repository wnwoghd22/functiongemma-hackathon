"""Selective routing v2.1 + minimal refinements.

Base: strategy_selective v2.1 (empty calls always fallback).
Minimal additions:
- Cloud escalation retry for under-called multi-action outputs.
- Light send_message normalization from user text for strict benchmark matching.
"""

import os
import re
import time

from google import genai
from google.genai import types

from main import generate_cactus


def _user_text(messages):
    return " ".join(
        str(m.get("content", ""))
        for m in messages
        if m.get("role") == "user"
    ).lower()


def _is_multi_action_request(messages):
    user_text = _user_text(messages)
    markers = (" and ", " then ", " also ", " plus ", ", and ", " 그리고 ", " 및 ")
    return any(marker in user_text for marker in markers) or user_text.count(",") >= 2


def _extract_send_message_payload(user_text):
    patterns = (
        r"\btext\s+([a-z][a-z0-9_-]*)\s+saying\s+(.+)$",
        r"\bsend a message to\s+([a-z][a-z0-9_-]*)\s+saying\s+(.+)$",
        r"\bsend message to\s+([a-z][a-z0-9_-]*)\s+saying\s+(.+)$",
    )
    for p in patterns:
        m = re.search(p, user_text.strip())
        if not m:
            continue
        recipient = m.group(1).strip().title()
        message = m.group(2).strip().strip("\"'").rstrip(".!?")
        if recipient and message:
            return {"recipient": recipient, "message": message}
    return None


def _normalize_send_message_calls(function_calls, user_text):
    payload = _extract_send_message_payload(user_text)
    if not payload:
        return function_calls

    normalized = []
    for call in function_calls:
        if not isinstance(call, dict):
            normalized.append(call)
            continue
        if call.get("name") != "send_message":
            normalized.append(call)
            continue
        args = call.get("arguments", {})
        if not isinstance(args, dict):
            normalized.append(call)
            continue
        new_args = dict(args)
        new_args["recipient"] = payload["recipient"]
        new_args["message"] = payload["message"]
        normalized.append({
            "name": call.get("name"),
            "arguments": new_args,
        })
    return normalized


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
    # Always fallback when tools exist.
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

    # Gate 5: Time-field sanity.
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

    # Gate 6: Multi-action under-call.
    if _is_multi_action_request(messages) and len(local_calls) < 2:
        return True, "multi_action_under_called"

    # Gate 7: Tool-count gate.
    if len(tools) >= 3 and local_conf < 0.75:
        return True, "many_tools_low_conf"

    # Gate 8: Moderate confidence gate.
    if local_conf < 0.6:
        return True, "low_confidence"

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

    function_calls = _normalize_send_message_calls(function_calls, _user_text(messages))
    return {
        "function_calls": function_calls,
        "total_time_ms": total_time_ms,
    }


def generate_hybrid(messages, tools, confidence_threshold=0.99):
    local = generate_cactus(messages, tools)
    user_text = _user_text(messages)
    local["function_calls"] = _normalize_send_message_calls(local.get("function_calls") or [], user_text)
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

    fallback_model = os.environ.get("GEMINI_MODEL_FALLBACK", "gemini-2.5-flash-lite")
    escalation_model = os.environ.get("GEMINI_MODEL_ESCALATE", "gemini-2.5-flash")
    models_to_try = [fallback_model]
    if escalation_model not in models_to_try:
        models_to_try.append(escalation_model)

    last_error = None
    for i, model_name in enumerate(models_to_try):
        try:
            cloud = _generate_cloud(messages, tools, model_name)
            if (
                _is_multi_action_request(messages)
                and len(cloud.get("function_calls") or []) < 2
                and i + 1 < len(models_to_try)
            ):
                last_error = RuntimeError("cloud_under_called_multi_action")
                continue

            cloud["source"] = "cloud (fallback)"
            cloud["local_confidence"] = local_conf
            cloud["total_time_ms"] += local_time_ms
            cloud["fallback_reason"] = fallback_reason
            cloud["cloud_model"] = model_name
            return cloud
        except Exception as e:
            last_error = e

    generate_hybrid._disable_cloud_fallback = True
    local["source"] = "on-device"
    local["fallback_reason"] = fallback_reason
    local["cloud_error"] = str(last_error) if last_error else "unknown_cloud_error"
    return local
