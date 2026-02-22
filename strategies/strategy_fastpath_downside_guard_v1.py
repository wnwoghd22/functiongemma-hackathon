"""Fast-path downside guard v1.

Design goals:
- Keep `main.py` unchanged.
- Keep fast-path speed gains only for very clear single-intent requests.
- Protect downside with explicit quality checks and on-device recovery pass.
"""

import copy
import re
import time

import main as core


_FASTPATH_TOOLS = {
    "get_weather",
    "set_alarm",
    "set_timer",
    "search_contacts",
    "play_music",
}

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


def _has_any(text, keywords):
    return any(k in text for k in keywords)


def _intent_expected_tools(user_text, tools):
    text = user_text.lower()
    names = {t.get("name") for t in tools if t.get("name")}
    expected = set()

    if "get_weather" in names and _has_any(text, ("weather", "temperature", "forecast", "outside", "rain", "snow")):
        expected.add("get_weather")
    if "set_alarm" in names and _has_any(text, ("alarm", "wake me", "wake up")):
        expected.add("set_alarm")
    if "set_timer" in names and _has_any(text, ("timer", "countdown", "minute", "minutes")):
        expected.add("set_timer")
    if "search_contacts" in names and _has_any(text, ("find ", "look up", "lookup", "search", "contacts", "phonebook")):
        expected.add("search_contacts")
    if "play_music" in names and _has_any(text, ("play ", "music", "song", "listen", "track", "tune")):
        expected.add("play_music")
    if "send_message" in names and _has_any(text, ("text ", "message", "send ", "tell ", "sms", "msg")):
        expected.add("send_message")
    if "create_reminder" in names and _has_any(text, ("remind", "reminder")):
        expected.add("create_reminder")

    return expected


def _is_filled(value):
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set, dict)):
        return len(value) > 0
    return True


def _required_missing(calls, tools):
    tool_map = {t.get("name"): t for t in tools if t.get("name")}
    for call in calls:
        if not isinstance(call, dict):
            return True
        name = call.get("name")
        args = call.get("arguments")
        if name not in tool_map or not isinstance(args, dict):
            return True
        for req in tool_map[name].get("parameters", {}).get("required", []):
            if req not in args or not _is_filled(args.get(req)):
                return True
    return False


def _suspicious_defaults(calls, user_text):
    text = user_text.lower()
    suspicious = 0
    for call in calls:
        if not isinstance(call, dict):
            suspicious += 1
            continue
        name = call.get("name")
        args = call.get("arguments", {})
        if not isinstance(args, dict):
            suspicious += 1
            continue
        if name == "set_alarm":
            h = args.get("hour")
            m = args.get("minute")
            if isinstance(h, int) and isinstance(m, int) and h == 0 and m == 0:
                if not _has_any(text, ("midnight", "12 am", "00:00")):
                    suspicious += 1
        elif name == "set_timer":
            minutes = args.get("minutes")
            if isinstance(minutes, int) and minutes <= 0:
                suspicious += 1
        elif name == "get_weather":
            loc = str(args.get("location", "")).strip().lower()
            if loc in {"", "here", "there", "outside"}:
                suspicious += 1
        elif name == "search_contacts":
            query = str(args.get("query", "")).strip().lower()
            if query in {"", "contact", "contacts"}:
                suspicious += 1
        elif name == "play_music":
            song = str(args.get("song", "")).strip().lower()
            if song in {"", "music", "song"}:
                suspicious += 1
    return suspicious


def _quality_score(result, messages, tools):
    calls = result.get("function_calls") or []
    user_text = _messages_to_user_text(messages)
    expected = _intent_expected_tools(user_text, tools)
    called = {
        c.get("name")
        for c in calls
        if isinstance(c, dict) and isinstance(c.get("name"), str)
    }

    required_missing = _required_missing(calls, tools) if calls else True
    is_multi = core._is_multi_action(user_text)
    multi_under_called = is_multi and len(calls) < 2
    coverage = 1.0 if not expected else len(called.intersection(expected)) / len(expected)
    suspicious = _suspicious_defaults(calls, user_text)

    score = 0.0
    score += 35.0 if calls else 0.0
    score += 30.0 if not required_missing else 0.0
    score += 25.0 * coverage
    score += 10.0 if not multi_under_called else 0.0
    score -= 8.0 * suspicious

    return score, {
        "calls": len(calls),
        "required_missing": required_missing,
        "multi_under_called": multi_under_called,
        "coverage": coverage,
        "suspicious": suspicious,
    }


def _required_valid(tool_name, args, tools, user_text):
    tool_map = {t.get("name"): t for t in tools if t.get("name")}
    if tool_name not in tool_map or not isinstance(args, dict):
        return False

    for req in tool_map[tool_name].get("parameters", {}).get("required", []):
        if req not in args or not _is_filled(args.get(req)):
            return False

    text = user_text.lower()
    if tool_name == "get_weather":
        loc = str(args.get("location", "")).strip().lower()
        if loc in {"", "here", "there", "outside"}:
            return False
    elif tool_name == "set_alarm":
        h = args.get("hour")
        m = args.get("minute")
        if not isinstance(h, int) or not isinstance(m, int):
            return False
        if not (0 <= h <= 23 and 0 <= m <= 59):
            return False
        if h == 0 and m == 0 and not _has_any(text, ("midnight", "12 am", "00:00")):
            return False
    elif tool_name == "set_timer":
        minutes = args.get("minutes")
        if not isinstance(minutes, int) or minutes <= 0:
            return False
    elif tool_name == "search_contacts":
        query = str(args.get("query", "")).strip().lower()
        if query in {"", "contact", "contacts"}:
            return False
    elif tool_name == "play_music":
        song = str(args.get("song", "")).strip()
        if len(song) < 2:
            return False
    return True


def _try_fastpath_guarded(user_text, tools):
    text = user_text.strip()
    text_l = text.lower()

    if len(text) > 100:
        return None
    if core._is_multi_action(text):
        return None
    if text.count(",") > 0:
        return None

    hits = _intent_expected_tools(text, tools)
    if len(hits) != 1:
        return None

    tool_name = next(iter(hits))
    if tool_name not in _FASTPATH_TOOLS:
        return None

    # Keep music fast-path narrow to avoid hidden overfit.
    if tool_name == "play_music" and not re.search(r"\bplay\s+.+", text_l):
        return None

    args = core._extract_args_for_tool(tool_name, text, {})
    sanitized = core._sanitize_function_calls([{"name": tool_name, "arguments": args}])
    if not sanitized:
        return None
    call = sanitized[0]
    if not isinstance(call, dict):
        return None
    call_args = call.get("arguments")
    if not isinstance(call_args, dict):
        return None

    if not _required_valid(tool_name, call_args, tools, text):
        return None

    return {"name": tool_name, "arguments": call_args}


def _word_or_num_to_hour(token):
    token = token.lower().strip()
    if token.isdigit():
        return int(token)
    return _NUMBER_WORDS.get(token)


def _normalize_user_text(text):
    def quarter_repl(match):
        h = _word_or_num_to_hour(match.group(1))
        return f"{h}:15" if h else match.group(0)

    def half_repl(match):
        h = _word_or_num_to_hour(match.group(1))
        return f"{h}:30" if h else match.group(0)

    out = re.sub(r"\bquarter\s+past\s+(\w+)\b", quarter_repl, text, flags=re.IGNORECASE)
    out = re.sub(r"\bhalf\s+past\s+(\w+)\b", half_repl, out, flags=re.IGNORECASE)
    out = re.sub(r"\bhalf\s+an\s+hour\b", "30 minutes", out, flags=re.IGNORECASE)
    out = re.sub(r"\bhalf\s+hour\b", "30 minutes", out, flags=re.IGNORECASE)
    out = re.sub(r"\bphonebook\b", "contacts", out, flags=re.IGNORECASE)
    out = re.sub(r"\bshoot\b", "text", out, flags=re.IGNORECASE)
    out = re.sub(r"\bping\b", "message", out, flags=re.IGNORECASE)
    if re.search(r"\boutside\b", out, flags=re.IGNORECASE) and not re.search(r"\bweather\b", out, flags=re.IGNORECASE):
        out = "weather " + out
    return out


def _normalize_messages(messages):
    norm = copy.deepcopy(messages)
    for m in norm:
        if m.get("role") != "user":
            continue
        m["content"] = _normalize_user_text(str(m.get("content", "")))
    return norm


def _dedup_calls(calls):
    seen = set()
    dedup = []
    for c in calls:
        key = core._call_dedup_key(c)
        if key in seen:
            continue
        seen.add(key)
        dedup.append(c)
    return dedup


def _run_primary(messages, tools, confidence_threshold=0.0):
    out = core._generate_hybrid_core(
        messages,
        tools,
        confidence_threshold=confidence_threshold,
        allow_cloud=False,
    )
    out["function_calls"] = core._sanitize_function_calls(out.get("function_calls", []))
    out["source"] = "on-device"
    out.setdefault("confidence", 1.0)
    out.setdefault("success", True)
    return out


def _run_recovery(messages, tools):
    norm_messages = _normalize_messages(messages)
    text = _messages_to_user_text(norm_messages)

    if core._is_multi_action(text):
        parts = core._split_multi_action(text)
        parts = core._resolve_pronouns_in_subrequests(parts, text)
        all_calls = []
        total_time = 0
        for p in parts:
            r = core._call_cactus_single(p, tools, confidence_threshold=0.0)
            all_calls.extend(r.get("function_calls", []))
            total_time += r.get("total_time_ms", 0)
        calls = core._sanitize_function_calls(_dedup_calls(all_calls))
        return {
            "function_calls": calls,
            "total_time_ms": total_time,
            "source": "on-device",
            "confidence": 1.0,
            "success": True,
        }

    r = core._call_cactus_single(text, tools, confidence_threshold=0.0)
    r["function_calls"] = core._sanitize_function_calls(r.get("function_calls", []))
    r["source"] = "on-device"
    r["confidence"] = 1.0
    r["success"] = True
    return r


def _choose_better(primary, recovery, messages, tools):
    q_primary, m_primary = _quality_score(primary, messages, tools)
    q_recovery, m_recovery = _quality_score(recovery, messages, tools)

    if q_recovery > q_primary + 1e-6:
        recovery["policy_tag"] = "fastpath_downside_guard_v1::recovery"
        recovery["quality_debug"] = {"primary": m_primary, "recovery": m_recovery}
        return recovery
    if q_primary > q_recovery + 1e-6:
        primary["policy_tag"] = "fastpath_downside_guard_v1::primary"
        primary["quality_debug"] = {"primary": m_primary, "recovery": m_recovery}
        return primary

    # Tie-breaker: prefer better intent coverage, then lower latency.
    if m_recovery["coverage"] > m_primary["coverage"]:
        recovery["policy_tag"] = "fastpath_downside_guard_v1::recovery_tie"
        recovery["quality_debug"] = {"primary": m_primary, "recovery": m_recovery}
        return recovery
    if m_primary["coverage"] > m_recovery["coverage"]:
        primary["policy_tag"] = "fastpath_downside_guard_v1::primary_tie"
        primary["quality_debug"] = {"primary": m_primary, "recovery": m_recovery}
        return primary

    if recovery.get("total_time_ms", 0) < primary.get("total_time_ms", 0):
        recovery["policy_tag"] = "fastpath_downside_guard_v1::recovery_time_tie"
        recovery["quality_debug"] = {"primary": m_primary, "recovery": m_recovery}
        return recovery

    primary["policy_tag"] = "fastpath_downside_guard_v1::primary_time_tie"
    primary["quality_debug"] = {"primary": m_primary, "recovery": m_recovery}
    return primary


def generate_hybrid(messages, tools, confidence_threshold=0.0):
    start = time.time()
    user_text = _messages_to_user_text(messages)

    fast = _try_fastpath_guarded(user_text, tools)
    if fast is not None:
        return {
            "function_calls": [fast],
            "total_time_ms": (time.time() - start) * 1000,
            "source": "on-device",
            "confidence": 1.0,
            "success": True,
            "policy_tag": f"fastpath_downside_guard_v1::fast::{fast.get('name')}",
        }

    primary = _run_primary(messages, tools, confidence_threshold=confidence_threshold)
    q_primary, m_primary = _quality_score(primary, messages, tools)

    if q_primary >= 90.0 and not m_primary["required_missing"] and not m_primary["multi_under_called"]:
        primary["policy_tag"] = "fastpath_downside_guard_v1::keep_primary"
        primary["quality_debug"] = {"primary": m_primary}
        return primary

    recovery = _run_recovery(messages, tools)
    return _choose_better(primary, recovery, messages, tools)
