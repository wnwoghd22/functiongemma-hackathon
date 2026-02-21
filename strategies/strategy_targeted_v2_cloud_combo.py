"""Targeted-v2 + selective cloud combo.

Design:
- Keep strategy_targeted_v2 as primary (high on-device performance).
- Only fallback to cloud on the empirically weak patterns:
  1) music_among_three-like
  2) reminder_among_four-like
  3) alarm_and_reminder-like
"""

import main as cloud_core
from strategies import strategy_targeted_v2 as local_core


def _messages_to_user_text(messages):
    return " ".join(
        str(m.get("content", ""))
        for m in messages
        if m.get("role") == "user"
    ).lower()


def _has_any(text, keywords):
    return any(k in text for k in keywords)


def _intent_flags(text):
    return {
        "alarm": _has_any(text, ("alarm", "wake me", "wake up")),
        "weather": _has_any(text, ("weather", "temperature", "forecast")),
        "message": _has_any(text, ("message", "text ", "send ", "saying", "tell ")),
        "reminder": _has_any(text, ("remind", "reminder")),
        "search": _has_any(text, ("find ", "look up", "search", "contacts")),
        "timer": _has_any(text, ("timer", "countdown", "minute")),
        "music": _has_any(text, ("play ", "music", "song", "listen")),
    }


def _is_multi(text):
    markers = (" and ", " then ", " also ", " plus ", ", and ")
    return any(m in text for m in markers) or text.count(",") >= 1


def _should_force_cloud(messages, tools):
    text = _messages_to_user_text(messages)
    flags = _intent_flags(text)
    multi = _is_multi(text)
    tool_count = len(tools)

    # 1) music_among_three-like
    if (not multi) and flags["music"] and tool_count == 3:
        return True, "sig_music_among_three"

    # 2) reminder_among_four-like
    if (not multi) and flags["reminder"] and tool_count == 4:
        return True, "sig_reminder_among_four"

    # 3) alarm_and_reminder-like
    if multi and flags["alarm"] and flags["reminder"] and not flags["weather"]:
        return True, "sig_alarm_and_reminder"

    return False, "on_device_primary"


def generate_hybrid(messages, tools, confidence_threshold=0.99):
    local = local_core.generate_hybrid(messages, tools, confidence_threshold=confidence_threshold)
    local["source"] = "on-device"

    force_cloud, policy = _should_force_cloud(messages, tools)
    local["policy_tag"] = policy
    if not force_cloud:
        return local

    try:
        cloud = cloud_core._generate_cloud(messages, tools)
        if cloud.get("function_calls"):
            cloud["source"] = "cloud (forced)"
            cloud["policy_tag"] = policy
            cloud["total_time_ms"] = cloud.get("total_time_ms", 0) + local.get("total_time_ms", 0)
            return cloud
        local["forced_cloud_empty"] = True
        return local
    except Exception as e:
        local["cloud_error"] = str(e)
        local["force_cloud"] = True
        return local
