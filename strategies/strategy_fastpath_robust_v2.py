"""Fast-path robust v2 (anti-overfit).

Design principles:
- High precision over coverage for fast-path.
- Only trigger fast-path on unambiguous single-intent requests.
- If uncertain, immediately fallback to `main.generate_hybrid`.
"""

import re
import time

import main as core


def _messages_to_user_text(messages):
    return " ".join(
        str(m.get("content", ""))
        for m in messages
        if m.get("role") == "user"
    )


def _has_any(text, keywords):
    return any(k in text for k in keywords)


def _intent_hits(user_text, tools):
    text = user_text.lower()
    names = {t.get("name") for t in tools if t.get("name")}
    hits = {}

    if "get_weather" in names:
        hits["get_weather"] = _has_any(
            text,
            ("weather", "temperature", "forecast", "outside", "rain", "snow", "sunny"),
        )
    if "set_alarm" in names:
        hits["set_alarm"] = _has_any(
            text,
            ("alarm", "wake me", "wake up", "wake-up"),
        )
    if "set_timer" in names:
        hits["set_timer"] = _has_any(
            text,
            ("timer", "countdown", "minute", "minutes", "second", "seconds"),
        )
    if "play_music" in names:
        hits["play_music"] = _has_any(
            text,
            ("play ", "music", "song", "listen", "track", "tune", "tunes"),
        )
    if "search_contacts" in names:
        hits["search_contacts"] = _has_any(
            text,
            ("find ", "look up", "lookup", "search", "contact", "contacts", "phonebook"),
        )
    if "send_message" in names:
        hits["send_message"] = _has_any(
            text,
            ("text ", "message", "send ", "tell ", "sms", "msg"),
        )
    if "create_reminder" in names:
        hits["create_reminder"] = _has_any(
            text,
            ("remind", "reminder"),
        )

    return {k: v for k, v in hits.items() if v}


def _is_unambiguous_single_intent(user_text, tools):
    text = user_text.strip()

    # Overly long or compound prompts are routed to core policy.
    if len(text) > 120:
        return False, None
    if core._is_multi_action(text):
        return False, None
    if text.count(",") >= 1:
        return False, None

    hits = _intent_hits(text, tools)
    if len(hits) != 1:
        return False, None

    return True, next(iter(hits.keys()))


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
    if tool_name not in tool_map or not isinstance(args, dict):
        return False

    required = tool_map[tool_name].get("parameters", {}).get("required", [])
    for req in required:
        if req not in args or not _is_filled(args.get(req)):
            return False

    text = user_text.lower()
    if tool_name == "set_alarm":
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
    elif tool_name == "get_weather":
        loc = str(args.get("location", "")).strip().lower()
        if loc in {"", "here", "there", "outside"}:
            return False
    elif tool_name == "search_contacts":
        q = str(args.get("query", "")).strip().lower()
        if q in {"", "contact", "contacts"}:
            return False
    elif tool_name == "play_music":
        song = str(args.get("song", "")).strip()
        if len(song) < 2:
            return False
    elif tool_name == "send_message":
        recipient = str(args.get("recipient", "")).strip()
        message = str(args.get("message", "")).strip()
        # Be strict to avoid hidden mismatch from weak extraction.
        if not recipient or not message:
            return False
        if len(message) < 2:
            return False
    elif tool_name == "create_reminder":
        title = str(args.get("title", "")).strip()
        time_str = str(args.get("time", "")).strip()
        # Be strict: reminder fast-path only on explicit title+time.
        if not title or not time_str:
            return False

    return True


def _safe_extract_args(tool_name, user_text):
    args = core._extract_args_for_tool(tool_name, user_text, {})
    sanitized = core._sanitize_function_calls([{"name": tool_name, "arguments": args}])
    if not sanitized:
        return None
    call = sanitized[0]
    if not isinstance(call, dict):
        return None
    out = call.get("arguments")
    if not isinstance(out, dict):
        return None
    return out


def _try_fastpath(user_text, tools):
    is_single, tool_name = _is_unambiguous_single_intent(user_text, tools)
    if not is_single:
        return None

    # Very conservative: for message/reminder, require explicit templates.
    text_l = user_text.lower()
    if tool_name == "send_message":
        if not (
            re.search(r'\bto\s+\w+\s+(?:saying|that)\s+', text_l)
            or re.search(r'\b(?:text|message)\s+\w+\s+', text_l)
        ):
            return None
    if tool_name == "create_reminder":
        if not re.search(r'\bremind(?:\s+me)?\b.+\bat\b', text_l):
            return None

    args = _safe_extract_args(tool_name, user_text)
    if args is None:
        return None
    if not _required_valid(tool_name, args, tools, user_text):
        return None

    return {"name": tool_name, "arguments": args}


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
            "policy_tag": f"fastpath_robust_v2::{fast.get('name')}",
        }

    # Uncertain or complex requests always use the base hybrid policy.
    out = core.generate_hybrid(messages, tools, confidence_threshold=confidence_threshold)
    out.setdefault("policy_tag", "fastpath_robust_v2::fallback_main")
    return out
