"""Overfit guard strategy v1 (main.py frozen).

Objectives:
- keep main.py unchanged
- improve robustness to paraphrased prompts
- use confidence_threshold=0.5 (model handoff signal enabled)
- add semantic guard: if intent-tool mismatch is detected, force cloud fallback
"""

import copy
import re

import main as core


_NUMBER_WORDS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
}


def _messages_to_user_text(messages):
    return " ".join(
        str(m.get("content", ""))
        for m in messages
        if m.get("role") == "user"
    )


def _word_or_num_to_hour(token):
    token = token.lower().strip()
    if token.isdigit():
        return int(token)
    return _NUMBER_WORDS.get(token)


def _normalize_time_phrases(text):
    # quarter past ten -> 10:15
    def quarter_repl(match):
        h = _word_or_num_to_hour(match.group(1))
        return f"{h}:15" if h else match.group(0)

    # half past seven -> 7:30
    def half_repl(match):
        h = _word_or_num_to_hour(match.group(1))
        return f"{h}:30" if h else match.group(0)

    out = re.sub(r"\bquarter\s+past\s+(\w+)\b", quarter_repl, text, flags=re.IGNORECASE)
    out = re.sub(r"\bhalf\s+past\s+(\w+)\b", half_repl, out, flags=re.IGNORECASE)
    out = re.sub(r"\bhalf\s+an\s+hour\b", "30 minutes", out, flags=re.IGNORECASE)
    out = re.sub(r"\bhalf\s+hour\b", "30 minutes", out, flags=re.IGNORECASE)
    return out


def _normalize_intent_aliases(text):
    out = text
    out = re.sub(r"\bphonebook\b", "contacts", out, flags=re.IGNORECASE)
    out = re.sub(r"\bshoot\b", "text", out, flags=re.IGNORECASE)
    out = re.sub(r"\bping\b", "message", out, flags=re.IGNORECASE)

    # Weather paraphrases
    if re.search(r"\boutside\b", out, flags=re.IGNORECASE) and not re.search(r"\bweather\b", out, flags=re.IGNORECASE):
        out = "weather " + out
    return out


def _normalize_messages(messages):
    norm = copy.deepcopy(messages)
    for m in norm:
        if m.get("role") != "user":
            continue
        content = str(m.get("content", ""))
        content = _normalize_time_phrases(content)
        content = _normalize_intent_aliases(content)
        m["content"] = content
    return norm


def _has_any(text, keywords):
    return any(k in text for k in keywords)


def _intent_flags(text):
    return {
        "alarm": _has_any(text, ("alarm", "wake me", "wake up")),
        "weather": _has_any(text, ("weather", "temperature", "forecast", "outside")),
        "message": _has_any(text, ("message", "text ", "send ", "saying", "tell ", "ping ", "shoot ")),
        "reminder": _has_any(text, ("remind", "reminder")),
        "search": _has_any(text, ("find ", "look up", "search", "contacts", "phonebook")),
        "timer": _has_any(text, ("timer", "countdown", "minute", "minutes", "hour", "hours")),
        "music": _has_any(text, ("play ", "music", "song", "listen")),
    }


def _is_multi(text):
    markers = (" and ", " then ", " also ", " plus ", ", and ")
    return any(m in text for m in markers)


def _is_filled(value):
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set, dict)):
        return len(value) > 0
    return True


def _required_missing(calls, tool_map):
    for c in calls:
        if not isinstance(c, dict):
            return True
        name = c.get("name")
        args = c.get("arguments", {})
        if name not in tool_map or not isinstance(args, dict):
            return True
        for req in tool_map[name].get("parameters", {}).get("required", []):
            if req not in args or not _is_filled(args.get(req)):
                return True
    return False


def _need_cloud_guard(messages, result, tools):
    if str(result.get("source", "")).startswith("cloud"):
        return False, "already_cloud"

    text = _messages_to_user_text(messages).lower()
    flags = _intent_flags(text)
    calls = result.get("function_calls") or []
    tool_map = {t.get("name"): t for t in tools if t.get("name")}
    tool_names = set(tool_map.keys())
    called = {
        c.get("name")
        for c in calls
        if isinstance(c, dict) and isinstance(c.get("name"), str)
    }

    if not calls:
        return True, "guard_empty_calls"
    if _required_missing(calls, tool_map):
        return True, "guard_missing_required"

    # Intent-tool mismatch guards
    if flags["weather"] and "get_weather" in tool_names and "get_weather" not in called:
        return True, "guard_weather_missing"
    if flags["timer"] and "set_timer" in tool_names and "set_timer" not in called:
        return True, "guard_timer_missing"
    if flags["message"] and "send_message" in tool_names and "send_message" not in called:
        return True, "guard_message_missing"
    if flags["reminder"] and "create_reminder" in tool_names and "create_reminder" not in called:
        return True, "guard_reminder_missing"
    if flags["alarm"] and "set_alarm" in tool_names and "set_alarm" not in called:
        return True, "guard_alarm_missing"

    # Multi-intent under-call guard
    intent_count = sum(1 for v in flags.values() if v)
    if _is_multi(text) and intent_count >= 2 and len(calls) < 2:
        return True, "guard_multi_under_called"

    return False, "guard_ok"


def _fallback_cloud(messages, tools, local, reason):
    try:
        cloud = core._generate_cloud(messages, tools)
        if cloud.get("function_calls"):
            cloud["source"] = "cloud (overfit-guard)"
            cloud["fallback_reason"] = reason
            cloud["local_time_ms"] = local.get("total_time_ms", 0)
            cloud["total_time_ms"] = cloud.get("total_time_ms", 0) + local.get("total_time_ms", 0)
            return cloud
        local["forced_cloud_empty"] = True
    except Exception as e:
        local["cloud_error"] = str(e)

    local["fallback_reason"] = reason
    return local


def generate_hybrid(messages, tools, confidence_threshold=0.5):
    # Confidence threshold intentionally elevated from 0.0 to leverage handoff signal.
    norm_messages = _normalize_messages(messages)
    local = core.generate_hybrid(norm_messages, tools, confidence_threshold=confidence_threshold)
    local["policy_tag"] = "overfit_guard_v1"

    need_cloud, reason = _need_cloud_guard(messages, local, tools)
    if not need_cloud:
        local["fallback_reason"] = reason
        return local

    return _fallback_cloud(messages, tools, local, reason)
