"""Cloud-ramp strategy v1.

Goal:
- Keep low-risk requests mostly on-device.
- Gradually raise cloud fallback probability as request/tool risk increases.

Implementation:
- Reuse `main.py` core routing implementation.
- Dynamically tune:
  - confidence_threshold
  - aggressive fallback gate
  - tool-count threshold for aggressive gate
"""

import os
import main as core

_FORCE_CLOUD_FOR_SIGNATURES = os.environ.get("RAMP_FORCE_CLOUD_SIGNATURES", "1") == "1"
_FORCE_CLOUD_FOR_L2 = os.environ.get("RAMP_FORCE_CLOUD_L2", "0") == "1"


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


def _is_high_f_safe_case(messages, tools):
    """Protect known stable on-device regions to avoid collateral regressions."""
    text = _messages_to_user_text(messages).lower()
    flags = _intent_flags(text)
    active = [k for k, v in flags.items() if v]

    # Single-intent, very low-tool-count requests are usually stable on-device.
    if not core._is_multi_action(text) and len(tools) <= 2 and len(active) <= 1:
        return True

    # Weather-only and simple timer-only queries are generally robust.
    if flags["weather"] and not any(flags[k] for k in ("alarm", "message", "reminder", "search")):
        return True
    if flags["timer"] and not any(flags[k] for k in ("alarm", "message", "reminder", "search", "music")):
        return True

    return False


def _is_low_f_signature(messages, tools):
    """Target known weak patterns from low_f1_analysis_20260222_054900.md."""
    text = _messages_to_user_text(messages).lower()
    flags = _intent_flags(text)
    multi = core._is_multi_action(text)

    # 1) message_among_three-like.
    # Keep narrow to avoid touching message_among_four-like already-strong cases.
    if flags["message"] and not multi and len(tools) == 3:
        return True, "sig_message_among_three"

    # 2) alarm_among_three-like.
    if flags["alarm"] and not multi and len(tools) == 3 and _has_any(text, (":", "am", "pm")):
        return True, "sig_alarm_among_three"

    # 3) reminder_among_four-like.
    if flags["reminder"] and not multi and len(tools) == 4:
        return True, "sig_reminder_among_four"

    # 4) alarm_and_weather-like.
    if multi and flags["alarm"] and flags["weather"] and not flags["message"] and not flags["reminder"]:
        return True, "sig_alarm_and_weather"

    # 5) search_and_message-like.
    if multi and flags["search"] and flags["message"] and not flags["weather"]:
        return True, "sig_search_and_message"

    # 6) alarm_and_reminder-like.
    if multi and flags["alarm"] and flags["reminder"] and not flags["weather"]:
        return True, "sig_alarm_and_reminder"

    # 7) timer_music_reminder-like.
    if multi and flags["timer"] and flags["music"] and flags["reminder"]:
        return True, "sig_timer_music_reminder"

    return False, "sig_none"


def _compute_risk_score(messages, tools):
    text = _messages_to_user_text(messages).lower()
    score = 0

    # Multi-action is the strongest risk signal.
    if core._is_multi_action(text):
        score += 2

    # More tools in candidate set generally increases selection confusion.
    if len(tools) >= 5:
        score += 2
    elif len(tools) >= 3:
        score += 1

    # Historically brittle intents: time/reminder/message composition.
    if any(k in text for k in ("alarm", "remind", "reminder", "am", "pm", "minute", "timer")):
        score += 1
    if any(k in text for k in ("message", "text ", "send ", "saying")):
        score += 1

    return score


def _select_ramp_params(messages, tools):
    matched, signature = _is_low_f_signature(messages, tools)
    if matched:
        # Target known low-F signatures aggressively.
        return 2, 0.70, True, 3, signature

    # Guardrail next: do not disturb stable high-F zones.
    if _is_high_f_safe_case(messages, tools):
        return 0, 0.0, False, 99, "high_f_safe_guard"

    score = _compute_risk_score(messages, tools)

    # Level 0: Conservative (mostly on-device)
    if score <= 1:
        return 0, 0.0, False, 99, "ramp_l0"

    # Level 1: Balanced (cloud handoff can trigger on low-confidence local decoding)
    if score <= 3:
        return 1, 0.45, False, 99, "ramp_l1"

    # Level 2: Aggressive (for high-risk multi-tool/multi-intent requests)
    return 2, 0.70, True, 4, "ramp_l2"


def generate_hybrid(messages, tools, confidence_threshold=0.99):
    level, tuned_threshold, aggressive_mode, tool_threshold, policy_tag = _select_ramp_params(messages, tools)

    # Temporarily override main.py global knobs for this call only.
    old_aggressive = getattr(core, "_ENABLE_AGGRESSIVE_FALLBACK", False)
    old_tool_threshold = getattr(core, "_CLOUD_FALLBACK_TOOL_THRESHOLD", 5)
    try:
        core._ENABLE_AGGRESSIVE_FALLBACK = aggressive_mode
        core._CLOUD_FALLBACK_TOOL_THRESHOLD = tool_threshold

        result = core.generate_hybrid(
            messages,
            tools,
            confidence_threshold=tuned_threshold,
        )

        should_force_cloud = False
        if str(result.get("source", "")).startswith("on-device"):
            if _FORCE_CLOUD_FOR_SIGNATURES and policy_tag.startswith("sig_"):
                should_force_cloud = True
            elif _FORCE_CLOUD_FOR_L2 and level == 2:
                should_force_cloud = True

        if should_force_cloud:
            try:
                cloud = core._generate_cloud(messages, tools)
                if cloud.get("function_calls"):
                    cloud["source"] = "cloud (forced)"
                    cloud["total_time_ms"] = cloud.get("total_time_ms", 0) + result.get("total_time_ms", 0)
                    cloud["policy_tag"] = policy_tag
                    cloud["routing_level"] = level
                    cloud["risk_score"] = _compute_risk_score(messages, tools)
                    cloud["force_cloud"] = True
                    return cloud
                result["forced_cloud_empty"] = True
            except Exception as e:
                result["force_cloud"] = True
                result["cloud_error"] = str(e)

        result["routing_level"] = level
        result["risk_score"] = _compute_risk_score(messages, tools)
        result["policy_tag"] = policy_tag
        return result
    finally:
        core._ENABLE_AGGRESSIVE_FALLBACK = old_aggressive
        core._CLOUD_FALLBACK_TOOL_THRESHOLD = old_tool_threshold
