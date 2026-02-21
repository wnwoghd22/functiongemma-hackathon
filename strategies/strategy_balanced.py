import os
import time

from google import genai
from google.genai import types

from main import generate_cactus


def _is_multi_action_request(messages):
    user_text = " ".join(
        str(m.get("content", ""))
        for m in messages
        if m.get("role") == "user"
    ).lower()
    markers = (" and ", " then ", " also ", " plus ", ", and ", " 그리고 ", " 및 ")
    return any(marker in user_text for marker in markers) or user_text.count(",") >= 2


def _should_fallback(local, messages, tools, confidence_threshold):
    local_calls = local.get("function_calls") or []
    local_conf = local.get("confidence", 0)
    local_time_ms = local.get("total_time_ms", 0)

    tool_by_name = {t.get("name"): t for t in tools if t.get("name")}
    valid_tool_names = set(tool_by_name.keys())

    # 1) Output integrity gate.
    if local_conf == 0 and local_time_ms == 0 and not local_calls:
        return True, "parse_fail_sentinel", True

    for call in local_calls:
        if not isinstance(call, dict):
            return True, "invalid_call_shape", True
        if not isinstance(call.get("name"), str):
            return True, "invalid_call_name", True
        if not isinstance(call.get("arguments"), dict):
            return True, "invalid_call_arguments", True
        if valid_tool_names and call["name"] not in valid_tool_names:
            return True, "unknown_tool_name", True

    # 2) Empty-call safety gate (balanced: not always fallback).
    if tools and not local_calls:
        if _is_multi_action_request(messages):
            return True, "empty_calls_multi_action", True
        if local_conf < 0.95:
            return True, "empty_calls_low_conf", True
        # Keep on-device for high-confidence, single-action empty-call outputs.
        return False, "empty_calls_but_kept", False

    # 3) Argument sanity gate.
    for call in local_calls:
        schema = tool_by_name.get(call["name"], {}).get("parameters", {})
        required = schema.get("required", [])
        properties = schema.get("properties", {})
        args = call.get("arguments", {})

        for req_key in required:
            value = args.get(req_key)
            if req_key not in args:
                return True, "missing_required_argument", True
            if value is None:
                return True, "null_required_argument", True
            if isinstance(value, str) and not value.strip():
                return True, "empty_required_string", True

        for key, prop in properties.items():
            if key not in args:
                continue
            value = args[key]
            prop_type = str(prop.get("type", "")).lower()

            if prop_type == "integer":
                if isinstance(value, bool):
                    return True, "invalid_integer_type", True
                if isinstance(value, float):
                    if not value.is_integer():
                        return True, "invalid_integer_value", True
                    value = int(value)
                if not isinstance(value, int):
                    return True, "invalid_integer_type", True

                if key == "hour" and not (0 <= value <= 23):
                    return True, "hour_out_of_range", True
                if key == "minute" and not (0 <= value <= 59):
                    return True, "minute_out_of_range", True
                if key == "minutes" and value < 0:
                    return True, "negative_minutes", True

    # 4) Multi-action risk gate (balanced: fallback only when weak confidence).
    if _is_multi_action_request(messages) and len(local_calls) < 2 and local_conf < 0.98:
        return True, "multi_action_under_called", True

    # 5) Confidence gate (balanced: use a much lower threshold than baseline).
    if local_conf < min(confidence_threshold, 0.85):
        return True, "very_low_confidence", False

    return False, "on_device_ok", False


def _generate_cloud_with_model(messages, tools, model_name):
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
    local = generate_cactus(messages, tools)
    local_conf = local.get("confidence", 0)
    local_time_ms = local.get("total_time_ms", 0)

    if getattr(generate_hybrid, "_disable_cloud_fallback", False):
        local["source"] = "on-device"
        return local

    needs_cloud, fallback_reason, critical = _should_fallback(
        local, messages, tools, confidence_threshold
    )
    if not needs_cloud:
        local["source"] = "on-device"
        local["fallback_reason"] = fallback_reason
        return local

    fallback_model = os.environ.get("GEMINI_MODEL_FALLBACK", "gemini-2.5-flash-lite")
    escalation_model = os.environ.get("GEMINI_MODEL_ESCALATE", "gemini-2.5-flash")
    models_to_try = [fallback_model]
    if critical and escalation_model not in models_to_try:
        models_to_try.append(escalation_model)

    last_error = None
    for model_name in models_to_try:
        try:
            cloud = _generate_cloud_with_model(messages, tools, model_name)
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
