"""Fast-path low-risk v3.

Conservative variant to reduce overfitting risk:
- Fast-path only for robust tools: weather, alarm, timer, search_contacts.
- message/reminder/music never fast-pathed.
- Everything else delegates to main.generate_hybrid.
"""

import re
import time

import main as core


_FASTPATH_TOOLS = {"get_weather", "set_alarm", "set_timer", "search_contacts"}


def _messages_to_user_text(messages):
    return " ".join(
        str(m.get("content", ""))
        for m in messages
        if m.get("role") == "user"
    )


def _has_any(text, keywords):
    return any(k in text for k in keywords)


def _detect_single_tool(user_text, tools):
    text = user_text.lower()
    names = {t.get("name") for t in tools if t.get("name")}
    candidates = set()

    if "get_weather" in names and _has_any(text, ("weather", "temperature", "forecast")):
        candidates.add("get_weather")
    if "set_alarm" in names and _has_any(text, ("alarm", "wake me", "wake up")):
        candidates.add("set_alarm")
    if "set_timer" in names and _has_any(text, ("timer", "countdown", "minute", "minutes")):
        candidates.add("set_timer")
    if "search_contacts" in names and _has_any(text, ("find ", "look up", "lookup", "search", "contacts", "phonebook")):
        candidates.add("search_contacts")

    if len(candidates) != 1:
        return None
    tool_name = next(iter(candidates))
    if tool_name not in _FASTPATH_TOOLS:
        return None
    return tool_name


def _is_filled(v):
    if v is None:
        return False
    if isinstance(v, str):
        return bool(v.strip())
    if isinstance(v, (list, tuple, set, dict)):
        return len(v) > 0
    return True


def _required_valid(tool_name, args, tools, user_text):
    tool_map = {t.get("name"): t for t in tools if t.get("name")}
    if tool_name not in tool_map:
        return False
    reqs = tool_map[tool_name].get("parameters", {}).get("required", [])
    for k in reqs:
        if k not in args or not _is_filled(args.get(k)):
            return False

    text = user_text.lower()
    if tool_name == "get_weather":
        loc = str(args.get("location", "")).strip().lower()
        if loc in {"", "here", "there"}:
            return False
    elif tool_name == "set_alarm":
        h = args.get("hour")
        m = args.get("minute")
        if not isinstance(h, int) or not isinstance(m, int):
            return False
        if h == 0 and m == 0 and not _has_any(text, ("12 am", "midnight", "00:00")):
            return False
    elif tool_name == "set_timer":
        minutes = args.get("minutes")
        if not isinstance(minutes, int) or minutes <= 0:
            return False
    elif tool_name == "search_contacts":
        q = str(args.get("query", "")).strip().lower()
        if q in {"", "contact", "contacts"}:
            return False
    return True


def _try_fastpath(user_text, tools):
    text = user_text.strip()
    if len(text) > 90:
        return None
    if core._is_multi_action(text):
        return None
    if "," in text:
        return None

    tool_name = _detect_single_tool(text, tools)
    if not tool_name:
        return None

    args = core._extract_args_for_tool(tool_name, text, {})
    sanitized = core._sanitize_function_calls([{"name": tool_name, "arguments": args}])
    if not sanitized:
        return None
    call = sanitized[0]
    if not isinstance(call, dict):
        return None
    call_args = call.get("arguments", {})
    if not isinstance(call_args, dict):
        return None

    if not _required_valid(tool_name, call_args, tools, text):
        return None

    return {"name": tool_name, "arguments": call_args}


def generate_hybrid(messages, tools, confidence_threshold=0.0):
    start = time.time()
    user_text = _messages_to_user_text(messages)
    fast = _try_fastpath(user_text, tools)
    if fast is not None:
        return {
            "function_calls": [fast],
            "total_time_ms": (time.time() - start) * 1000,
            "source": "on-device",
            "confidence": 1.0,
            "success": True,
            "policy_tag": f"fastpath_lowrisk_v3::{fast.get('name')}",
        }

    out = core.generate_hybrid(messages, tools, confidence_threshold=confidence_threshold)
    out.setdefault("policy_tag", "fastpath_lowrisk_v3::fallback_main")
    return out
