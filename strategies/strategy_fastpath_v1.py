"""Fast-path strategy v1.

Approach:
- For simple single-intent requests, skip model inference and return
  deterministic rule-based calls immediately.
- For everything else, fallback to strategy_final_ensemble_v1.
"""

import re
import time

import main as core
from strategies import strategy_final_ensemble_v1 as base


def _messages_to_user_text(messages):
    return " ".join(
        str(m.get("content", ""))
        for m in messages
        if m.get("role") == "user"
    )


def _has_any(text, keywords):
    return any(k in text for k in keywords)


def _detect_expected_tools(user_text, tools):
    names = {t.get("name") for t in tools if t.get("name")}
    text = user_text.lower()
    expected = set()

    if _has_any(text, ("weather", "temperature", "forecast", "outside")) and "get_weather" in names:
        expected.add("get_weather")
    if _has_any(text, ("alarm", "wake me", "wake up")) and "set_alarm" in names:
        expected.add("set_alarm")
    if _has_any(text, ("message", "text ", "send ", "saying", "tell ", "ping ", "shoot ")) and "send_message" in names:
        expected.add("send_message")
    if _has_any(text, ("remind", "reminder")) and "create_reminder" in names:
        expected.add("create_reminder")
    if _has_any(text, ("find ", "look up", "search", "contacts", "phonebook")) and "search_contacts" in names:
        expected.add("search_contacts")
    if _has_any(text, ("play ", "music", "song", "listen")) and "play_music" in names:
        expected.add("play_music")
    if _has_any(text, ("timer", "countdown", "minute", "minutes")) and "set_timer" in names:
        expected.add("set_timer")

    return expected


def _is_filled(value):
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set, dict)):
        return len(value) > 0
    return True


def _required_valid(tool_name, args, tools):
    tool_map = {t.get("name"): t for t in tools if t.get("name")}
    if tool_name not in tool_map or not isinstance(args, dict):
        return False

    required = tool_map[tool_name].get("parameters", {}).get("required", [])
    for key in required:
        if key not in args or not _is_filled(args.get(key)):
            return False

    # Extra conservative checks to avoid low-quality fast path output.
    if tool_name == "set_timer":
        return isinstance(args.get("minutes"), int) and args["minutes"] > 0
    if tool_name == "set_alarm":
        h = args.get("hour")
        m = args.get("minute")
        if not isinstance(h, int) or not isinstance(m, int):
            return False
        # 00:00 is likely parser fallback for unknown time, avoid fast-path in that case.
        return not (h == 0 and m == 0)
    if tool_name == "send_message":
        return _is_filled(args.get("recipient")) and _is_filled(args.get("message"))
    if tool_name == "create_reminder":
        return _is_filled(args.get("title")) and _is_filled(args.get("time"))
    if tool_name == "get_weather":
        return _is_filled(args.get("location"))
    if tool_name == "search_contacts":
        return _is_filled(args.get("query"))
    if tool_name == "play_music":
        return _is_filled(args.get("song"))

    return True


def _try_fastpath(user_text, tools):
    # Reuse normalization from the ensemble strategy to improve robustness.
    normalized = base._normalize_user_text(user_text)
    expected = _detect_expected_tools(normalized, tools)

    # Fast-path only for clear single-intent and non-compound requests.
    if len(expected) != 1:
        return None
    if core._is_multi_action(normalized) or "," in normalized:
        return None

    tool_name = next(iter(expected))
    args = core._extract_args_for_tool(tool_name, normalized, {})
    call = {"name": tool_name, "arguments": args}
    sanitized = core._sanitize_function_calls([call])
    if not sanitized:
        return None
    call = sanitized[0]
    if not isinstance(call, dict) or not isinstance(call.get("arguments"), dict):
        return None

    if not _required_valid(tool_name, call["arguments"], tools):
        return None
    return call


def generate_hybrid(messages, tools, confidence_threshold=0.0):
    start = time.time()
    user_text = _messages_to_user_text(messages)

    fast_call = _try_fastpath(user_text, tools)
    if fast_call is not None:
        elapsed = (time.time() - start) * 1000
        return {
            "function_calls": [fast_call],
            "total_time_ms": elapsed,
            "source": "on-device",
            "confidence": 1.0,
            "success": True,
            "policy_tag": f"fastpath_v1::{fast_call.get('name')}",
        }

    return base.generate_hybrid(messages, tools, confidence_threshold=confidence_threshold)
