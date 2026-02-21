"""Refined routing strategy tuned for F1/latency/on-device trade-off.

Design goals:
- Recover medium-difficulty tool-selection failures without sending everything to cloud.
- Keep obviously safe single-intent cases on-device.
- Add cloud escalation for hard/critical failures.
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


def _is_multi_action_request(user_text):
    markers = (" and ", " then ", " also ", " plus ", ", and ", " 그리고 ", " 및 ")
    return any(marker in user_text for marker in markers) or user_text.count(",") >= 2


def _extract_intents(user_text):
    intent_map = {
        "get_weather": ("weather", "temperature", "forecast", "climate"),
        "set_alarm": ("alarm", "wake me up", "wake-up"),
        "set_timer": ("timer", "countdown"),
        "create_reminder": ("remind me", "reminder"),
        "send_message": ("send a message", "send message", "text ", "message "),
        "search_contacts": ("look up", "find ", "search ", "contacts"),
        "play_music": ("play ", "music", "song"),
    }
    intents = set()
    for tool_name, keywords in intent_map.items():
        if any(k in user_text for k in keywords):
            intents.add(tool_name)
    return intents


def _extract_time_from_text(user_text):
    m = re.search(r"\b(\d{1,2})\s*:\s*(\d{2})\s*(am|pm)?\b", user_text)
    if m:
        hour = int(m.group(1))
        minute = int(m.group(2))
        meridiem = m.group(3)
        if meridiem == "pm" and hour != 12:
            hour += 12
        elif meridiem == "am" and hour == 12:
            hour = 0
        return hour % 24, minute

    m = re.search(r"\b(\d{1,2})\s*(am|pm)\b", user_text)
    if m:
        hour = int(m.group(1))
        minute = 0
        meridiem = m.group(2)
        if meridiem == "pm" and hour != 12:
            hour += 12
        elif meridiem == "am" and hour == 12:
            hour = 0
        return hour % 24, minute

    return None


def _extract_recipient_from_text(user_text):
    for pattern in (
        r"\bto\s+([a-z][a-z0-9_-]*)\b",
        r"\btext\s+([a-z][a-z0-9_-]*)\b",
        r"\bmessage\s+([a-z][a-z0-9_-]*)\b",
    ):
        m = re.search(pattern, user_text)
        if m:
            return m.group(1)
    return None


def _cloud_retry_needed(cloud_calls, user_text):
    if _is_multi_action_request(user_text) and len(cloud_calls) < 2:
        return True, "cloud_under_called_multi_action"
    if not cloud_calls:
        return True, "cloud_empty_calls"
    return False, "cloud_ok"


def _should_fallback(local, messages, tools, confidence_threshold):
    user_text = _user_text(messages)
    multi_action = _is_multi_action_request(user_text)
    intents = _extract_intents(user_text)

    local_calls = local.get("function_calls") or []
    local_conf = float(local.get("confidence", 0) or 0)
    local_time_ms = float(local.get("total_time_ms", 0) or 0)

    tool_by_name = {t.get("name"): t for t in tools if t.get("name")}
    valid_tool_names = set(tool_by_name.keys())

    # Gate 1: parse-fail sentinel.
    if local_conf == 0 and local_time_ms == 0 and not local_calls:
        return True, "parse_fail_sentinel", True

    # Gate 2: structural validation.
    for call in local_calls:
        if not isinstance(call, dict):
            return True, "invalid_call_shape", True
        if not isinstance(call.get("name"), str):
            return True, "invalid_call_name", True
        if not isinstance(call.get("arguments"), dict):
            return True, "invalid_call_arguments", True
        if valid_tool_names and call["name"] not in valid_tool_names:
            return True, "unknown_tool_name", True

    # Gate 3: empty-call handling.
    if tools and not local_calls:
        if multi_action:
            return True, "empty_calls_multi_action", True
        if len(tools) >= 3 and local_conf < 0.90:
            return True, "empty_calls_ambiguous_toolset", False
        if local_conf < 0.78:
            return True, "empty_calls_low_conf", False
        return False, "empty_calls_kept", False

    # Gate 4: required arguments and trivial range checks.
    for call in local_calls:
        schema = tool_by_name.get(call["name"], {}).get("parameters", {})
        required = schema.get("required", [])
        properties = schema.get("properties", {})
        args = call.get("arguments", {})

        for req_key in required:
            if req_key not in args:
                return True, "missing_required_argument", True
            value = args.get(req_key)
            if value is None:
                return True, "null_required_argument", True
            if isinstance(value, str) and not value.strip():
                return True, "empty_required_string", True

        for key, prop in properties.items():
            if key not in args:
                continue
            value = args[key]
            prop_type = str(prop.get("type", "")).lower()
            if prop_type != "integer":
                continue
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
            if key in ("minutes", "seconds", "duration") and value < 0:
                return True, "negative_time_value", True

    # Gate 5: multi-action under-call.
    if multi_action and len(local_calls) < 2:
        return True, "multi_action_under_called", True

    # Gate 6: intent/tool mismatch for single-action requests.
    if len(intents) == 1 and len(local_calls) == 1:
        expected_tool = next(iter(intents))
        predicted_tool = local_calls[0].get("name")
        if expected_tool != predicted_tool:
            return True, "intent_tool_mismatch", False

    # Gate 7: ambiguous toolset + low confidence.
    if not multi_action and len(tools) >= 3 and local_conf < confidence_threshold:
        return True, "ambiguous_tools_low_conf", False

    # Gate 8: semantic spot-check for alarm and message.
    for call in local_calls:
        name = call.get("name")
        args = call.get("arguments", {})
        if name == "set_alarm":
            parsed_time = _extract_time_from_text(user_text)
            if parsed_time:
                exp_hour, exp_minute = parsed_time
                got_hour = args.get("hour")
                got_minute = args.get("minute")
                if isinstance(got_hour, int) and isinstance(got_minute, int):
                    if got_hour != exp_hour or got_minute != exp_minute:
                        return True, "alarm_time_mismatch", False
        if name == "send_message":
            recipient = _extract_recipient_from_text(user_text)
            got = args.get("recipient")
            if recipient and isinstance(got, str) and got.strip():
                if got.strip().lower() != recipient.strip().lower():
                    return True, "recipient_mismatch", False

    # Gate 9: safety floor for very low confidence.
    if local_conf < 0.60:
        return True, "very_low_confidence", False

    return False, "on_device_ok", False


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


def generate_hybrid(messages, tools, confidence_threshold=0.83):
    local = generate_cactus(messages, tools)
    local_conf = local.get("confidence", 0)
    local_time_ms = local.get("total_time_ms", 0)
    user_text = _user_text(messages)

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
    for idx, model_name in enumerate(models_to_try):
        try:
            cloud = _generate_cloud(messages, tools, model_name)
            retry, retry_reason = _cloud_retry_needed(cloud["function_calls"], user_text)
            if retry and idx + 1 < len(models_to_try):
                last_error = RuntimeError(retry_reason)
                continue

            cloud["source"] = "cloud (fallback)"
            cloud["local_confidence"] = local_conf
            cloud["total_time_ms"] += local_time_ms
            cloud["fallback_reason"] = fallback_reason
            cloud["cloud_model"] = model_name
            if retry:
                cloud["cloud_warning"] = retry_reason
            return cloud
        except Exception as e:
            last_error = e

    generate_hybrid._disable_cloud_fallback = True
    local["source"] = "on-device"
    local["fallback_reason"] = fallback_reason
    local["cloud_error"] = str(last_error) if last_error else "unknown_cloud_error"
    return local
