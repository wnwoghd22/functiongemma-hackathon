"""Final ensemble strategy v1.

Goals:
- Keep `main.py` unchanged.
- Improve robustness for hidden phrasing drift with minimal risk.
- Prefer on-device recovery pass before accepting low-quality output.
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
    return out


def _normalize_aliases(text):
    out = text
    out = re.sub(r"\bphonebook\b", "contacts", out, flags=re.IGNORECASE)
    out = re.sub(r"\bshoot\b", "text", out, flags=re.IGNORECASE)
    out = re.sub(r"\bping\b", "message", out, flags=re.IGNORECASE)
    if re.search(r"\boutside\b", out, flags=re.IGNORECASE) and not re.search(r"\bweather\b", out, flags=re.IGNORECASE):
        out = "weather " + out
    return out


def _normalize_user_text(text):
    return _normalize_aliases(_normalize_time_phrases(text))


def _normalize_messages(messages):
    norm = copy.deepcopy(messages)
    for m in norm:
        if m.get("role") != "user":
            continue
        m["content"] = _normalize_user_text(str(m.get("content", "")))
    return norm


def _has_any(text, keywords):
    return any(k in text for k in keywords)


def _intent_expected_tools(text, available_tools):
    names = {t.get("name") for t in available_tools if t.get("name")}
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
    if _has_any(text, ("timer", "countdown", "minute", "minutes")) and "set_timer" in names:
        expected.add("set_timer")
    if _has_any(text, ("play ", "music", "song", "listen")) and "play_music" in names:
        expected.add("play_music")

    return expected


def _is_filled(value):
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set, dict)):
        return len(value) > 0
    return True


def _has_required_missing(calls, tools):
    tool_map = {t.get("name"): t for t in tools if t.get("name")}
    for c in calls:
        if not isinstance(c, dict):
            return True
        name = c.get("name")
        args = c.get("arguments")
        if name not in tool_map or not isinstance(args, dict):
            return True
        required = tool_map[name].get("parameters", {}).get("required", [])
        for req in required:
            if req not in args or not _is_filled(args.get(req)):
                return True
    return False


def _quality_score(result, messages, tools):
    calls = result.get("function_calls") or []
    user_text = _messages_to_user_text(messages).lower()
    expected = _intent_expected_tools(user_text, tools)
    called = {
        c.get("name")
        for c in calls
        if isinstance(c, dict) and isinstance(c.get("name"), str)
    }

    missing_required = _has_required_missing(calls, tools) if calls else True
    multi_under_called = core._is_multi_action(user_text) and len(calls) < 2
    coverage = 1.0 if not expected else len(called.intersection(expected)) / max(1, len(expected))

    score = 0.0
    score += 50.0 if calls else 0.0
    score += 25.0 if not missing_required else 0.0
    score += 20.0 * coverage
    score += 5.0 if not multi_under_called else 0.0

    return score, {
        "missing_required": missing_required,
        "multi_under_called": multi_under_called,
        "coverage": coverage,
        "calls": len(calls),
    }


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


def _ondevice_recovery(messages, tools):
    text = _messages_to_user_text(messages)
    text = _normalize_user_text(text)

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


def _choose_better(a, b, messages, tools):
    qa, ma = _quality_score(a, messages, tools)
    qb, mb = _quality_score(b, messages, tools)
    if qb > qa:
        b["policy_tag"] = "final_ensemble_v1_recovery"
        b["quality_debug"] = {"primary": ma, "recovery": mb}
        return b
    a["policy_tag"] = "final_ensemble_v1_primary"
    a["quality_debug"] = {"primary": ma, "recovery": mb}
    return a


def generate_hybrid(messages, tools, confidence_threshold=0.0):
    primary = core.generate_hybrid(messages, tools, confidence_threshold=confidence_threshold)

    # If cloud already produced valid calls, keep it.
    if str(primary.get("source", "")).startswith("cloud") and primary.get("function_calls"):
        primary["policy_tag"] = "final_ensemble_v1_cloud_keep"
        return primary

    q_primary, meta = _quality_score(primary, messages, tools)

    # Fast path: keep strong outputs.
    if q_primary >= 92 and not meta["missing_required"] and not meta["multi_under_called"]:
        primary["policy_tag"] = "final_ensemble_v1_keep"
        return primary

    # Pass 2: normalized messages through main policy.
    norm_messages = _normalize_messages(messages)
    secondary = core.generate_hybrid(norm_messages, tools, confidence_threshold=confidence_threshold)
    best = _choose_better(primary, secondary, messages, tools)

    # Pass 3: strict on-device recovery only when still weak.
    q_best, _ = _quality_score(best, messages, tools)
    if q_best < 90:
        recovery = _ondevice_recovery(messages, tools)
        best = _choose_better(best, recovery, messages, tools)

    return best
