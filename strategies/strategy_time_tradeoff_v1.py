"""Score-aware tradeoff strategy.

Goal:
- Keep strong on-device outputs local.
- Force cloud only when estimated score gain is positive after losing on-device bonus.

Per-case proxy objective:
  delta = 0.60*(F1_cloud - F1_local) + 0.15*(T_cloud - T_local) - 0.25
Where T = max(0, 1 - time_ms/500).
Cloud T is conservatively assumed ~0 for routing decisions.
"""

import main as cloud_core
from strategies import strategy_targeted_v2 as local_core


def _messages_to_user_text(messages):
    return " ".join(
        str(m.get("content", ""))
        for m in messages
        if m.get("role") == "user"
    )


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
    return any(m in text for m in markers)


def _is_filled(value):
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set, dict)):
        return len(value) > 0
    return True


def _build_tool_map(tools):
    return {t.get("name"): t for t in tools if t.get("name")}


def _estimate_local_f1(local_result, messages, tools):
    text = _messages_to_user_text(messages).lower()
    flags = _intent_flags(text)
    multi = _is_multi(text)
    calls = local_result.get("function_calls") or []
    tool_map = _build_tool_map(tools)
    tool_names = set(tool_map.keys())
    called_names = {
        c.get("name")
        for c in calls
        if isinstance(c, dict) and isinstance(c.get("name"), str)
    }

    reasons = []
    est = 1.0

    if not calls:
        est = 0.0
        reasons.append("empty_calls")

    for call in calls:
        if not isinstance(call, dict):
            est = min(est, 0.0)
            reasons.append("invalid_call_shape")
            continue
        name = call.get("name")
        args = call.get("arguments")

        if not isinstance(name, str) or name not in tool_names:
            est = min(est, 0.0)
            reasons.append("unknown_tool")
            continue

        if not isinstance(args, dict):
            est = min(est, 0.0)
            reasons.append("invalid_args_shape")
            continue

        required = tool_map.get(name, {}).get("parameters", {}).get("required", [])
        missing_req = False
        for req in required:
            if req not in args or not _is_filled(args.get(req)):
                missing_req = True
                break
        if missing_req:
            est = min(est, 0.3)
            reasons.append(f"missing_required:{name}")

    # Multi-intent under-call usually maps to partial F1 region.
    intent_count = sum(1 for v in flags.values() if v)
    if multi and intent_count >= 2 and len(calls) < 2:
        est = min(est, 0.5)
        reasons.append("multi_under_called")

    # Known weak combination families.
    if (
        flags["reminder"]
        and "create_reminder" in tool_names
        and len(tools) >= 4
        and "create_reminder" not in called_names
    ):
        est = min(est, 0.4)
        reasons.append("reminder_missing_in_many_tools")

    if (
        multi
        and flags["alarm"]
        and flags["reminder"]
        and {"set_alarm", "create_reminder"}.issubset(tool_names)
        and not {"set_alarm", "create_reminder"}.issubset(called_names)
    ):
        est = min(est, 0.5)
        reasons.append("alarm_reminder_incomplete")

    if (
        multi
        and flags["weather"]
        and flags["message"]
        and {"get_weather", "send_message"}.issubset(tool_names)
        and not {"get_weather", "send_message"}.issubset(called_names)
    ):
        est = min(est, 0.5)
        reasons.append("weather_message_incomplete")

    est = max(0.0, min(1.0, est))
    return est, reasons


def _estimate_cloud_f1(local_f1_est):
    # Conservative prior: cloud often helps weak local outputs, but not always perfect.
    if local_f1_est <= 0.3:
        return 0.98
    if local_f1_est <= 0.5:
        return 0.95
    if local_f1_est <= 0.67:
        return 0.90
    return 0.88


def _time_score(ms):
    return max(0.0, 1.0 - (float(ms) / 500.0))


def _should_force_cloud(local_result, messages, tools):
    local_f1_est, reasons = _estimate_local_f1(local_result, messages, tools)
    cloud_f1_est = _estimate_cloud_f1(local_f1_est)

    local_t = _time_score(local_result.get("total_time_ms", 0.0))
    cloud_t = 0.0  # conservative estimate for routing

    delta = 0.60 * (cloud_f1_est - local_f1_est) + 0.15 * (cloud_t - local_t) - 0.25

    # Keep the policy strict: only force cloud when the estimated score delta is positive.
    should = delta > 0.0

    return should, {
        "local_f1_est": round(local_f1_est, 3),
        "cloud_f1_est": round(cloud_f1_est, 3),
        "local_time_score": round(local_t, 3),
        "cloud_time_score": round(cloud_t, 3),
        "score_delta_est": round(delta, 4),
        "reasons": reasons,
    }


def generate_hybrid(messages, tools, confidence_threshold=0.99):
    local = local_core.generate_hybrid(messages, tools, confidence_threshold=confidence_threshold)
    local["source"] = "on-device"

    force_cloud, analysis = _should_force_cloud(local, messages, tools)
    local["policy_tag"] = "tradeoff_v1"
    local["tradeoff_analysis"] = analysis

    if not force_cloud:
        local["tradeoff_decision"] = "keep_on_device"
        return local

    try:
        cloud = cloud_core._generate_cloud(messages, tools)
        if cloud.get("function_calls"):
            cloud["source"] = "cloud (tradeoff)"
            cloud["policy_tag"] = "tradeoff_v1"
            cloud["tradeoff_analysis"] = analysis
            cloud["total_time_ms"] = cloud.get("total_time_ms", 0) + local.get("total_time_ms", 0)
            return cloud
        local["tradeoff_decision"] = "cloud_empty_keep_local"
        local["forced_cloud_empty"] = True
        return local
    except Exception as e:
        local["tradeoff_decision"] = "cloud_error_keep_local"
        local["cloud_error"] = str(e)
        return local
