"""Fast-path downside guard v2.

Adds narrow pattern-based fixes on top of v1:
- single-intent reminder repair
- alarm+reminder multi-intent completion
"""

import copy
import re

import main as core
from strategies import strategy_fastpath_downside_guard_v1 as base


def _tool_names(tools):
    return {t.get("name") for t in tools if t.get("name")}


def _is_filled(value):
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set, dict)):
        return len(value) > 0
    return True


def _valid_alarm_args(args):
    if not isinstance(args, dict):
        return False
    h = args.get("hour")
    m = args.get("minute")
    return isinstance(h, int) and isinstance(m, int) and 0 <= h <= 23 and 0 <= m <= 59


def _valid_reminder_args(args):
    if not isinstance(args, dict):
        return False
    return _is_filled(args.get("title")) and _is_filled(args.get("time"))


def _dedup_calls(calls):
    seen = set()
    out = []
    for call in calls:
        key = core._call_dedup_key(call)
        if key in seen:
            continue
        seen.add(key)
        out.append(call)
    return out


def _build_single_reminder_fix(messages, tools, result):
    text = base._messages_to_user_text(messages)
    text_l = text.lower()
    names = _tool_names(tools)
    if "create_reminder" not in names:
        return None
    if core._is_multi_action(text):
        return None
    if not re.search(r"\bremind(?:\s+me)?\b.+\bat\b", text_l):
        return None

    called = {
        c.get("name")
        for c in (result.get("function_calls") or [])
        if isinstance(c, dict) and isinstance(c.get("name"), str)
    }
    if "create_reminder" in called:
        return None

    norm_text = base._normalize_user_text(text)
    args = core._extract_args_for_tool("create_reminder", norm_text, {})
    if not _valid_reminder_args(args):
        return None

    candidate = copy.deepcopy(result)
    candidate["function_calls"] = [{"name": "create_reminder", "arguments": args}]
    candidate["function_calls"] = core._sanitize_function_calls(candidate["function_calls"])
    candidate["source"] = "on-device"
    candidate["confidence"] = 1.0
    candidate["success"] = True
    candidate["policy_tag"] = "fastpath_downside_guard_v2::single_reminder_fix"
    return candidate


def _build_alarm_reminder_multi_fix(messages, tools, result):
    text = base._messages_to_user_text(messages)
    text_l = text.lower()
    names = _tool_names(tools)
    if not {"set_alarm", "create_reminder"}.issubset(names):
        return None
    if not core._is_multi_action(text):
        return None
    if "alarm" not in text_l or "remind" not in text_l:
        return None

    calls = list(result.get("function_calls") or [])
    called = {
        c.get("name")
        for c in calls
        if isinstance(c, dict) and isinstance(c.get("name"), str)
    }

    norm_text = base._normalize_user_text(text)
    parts = core._split_multi_action(norm_text)
    parts = core._resolve_pronouns_in_subrequests(parts, norm_text)

    alarm_call = None
    reminder_call = None
    for part in parts:
        p_l = part.lower()
        if alarm_call is None and any(k in p_l for k in ("alarm", "wake me", "wake up")):
            alarm_args = core._extract_args_for_tool("set_alarm", part, {})
            if _valid_alarm_args(alarm_args):
                alarm_call = {"name": "set_alarm", "arguments": alarm_args}
        if reminder_call is None and "remind" in p_l:
            reminder_args = core._extract_args_for_tool("create_reminder", part, {})
            if _valid_reminder_args(reminder_args):
                reminder_call = {"name": "create_reminder", "arguments": reminder_args}

    # Fallback extraction from full text when split extraction misses one side.
    if alarm_call is None and "set_alarm" not in called:
        alarm_args = core._extract_args_for_tool("set_alarm", norm_text, {})
        if _valid_alarm_args(alarm_args):
            alarm_call = {"name": "set_alarm", "arguments": alarm_args}
    if reminder_call is None and "create_reminder" not in called:
        reminder_args = core._extract_args_for_tool("create_reminder", norm_text, {})
        if _valid_reminder_args(reminder_args):
            reminder_call = {"name": "create_reminder", "arguments": reminder_args}

    if alarm_call is None and "set_alarm" not in called:
        return None
    if reminder_call is None and "create_reminder" not in called:
        return None

    merged = list(calls)
    if alarm_call is not None and "set_alarm" not in called:
        merged.append(alarm_call)
    if reminder_call is not None and "create_reminder" not in called:
        merged.append(reminder_call)

    merged = core._sanitize_function_calls(_dedup_calls(merged))
    candidate = copy.deepcopy(result)
    candidate["function_calls"] = merged
    candidate["source"] = "on-device"
    candidate["confidence"] = 1.0
    candidate["success"] = True
    candidate["policy_tag"] = "fastpath_downside_guard_v2::alarm_reminder_multi_fix"
    return candidate


def _choose_best(messages, tools, current_result, candidates):
    best = current_result
    best_score, _ = base._quality_score(best, messages, tools)
    for cand in candidates:
        if cand is None:
            continue
        score, _ = base._quality_score(cand, messages, tools)
        if score > best_score + 1e-6:
            best = cand
            best_score = score
    return best


def generate_hybrid(messages, tools, confidence_threshold=0.0):
    result = base.generate_hybrid(messages, tools, confidence_threshold=confidence_threshold)
    candidates = [
        _build_single_reminder_fix(messages, tools, result),
        _build_alarm_reminder_multi_fix(messages, tools, result),
    ]
    return _choose_best(messages, tools, result, candidates)
