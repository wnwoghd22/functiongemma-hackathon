"""Final on-device strategy v1: Enhanced strategy_targeted_v2 with targeted improvements.

Changes from strategy_targeted_v2:
1. Tool pruning: keyword-based filtering before cactus call reduces confusion with 4-5 tools
2. Enhanced tool descriptions: clearer descriptions help the 270M model pick correctly
3. Post-cactus keyword validation: override wrong tool picks when keyword evidence is unambiguous
4. Multi-action missing intent recovery: detect and synthesize missing calls in compound requests
5. Pure on-device: no cloud fallback code
"""

import json
import os
import re
import sys
import time

sys.path.insert(0, "cactus/python/src")
from cactus import cactus_init, cactus_complete, cactus_destroy, cactus_reset

_FUNCTIONGEMMA_PATH = "cactus/weights/functiongemma-270m-it"
_CACTUS_GLOBAL_MODEL = None


def _get_model():
    global _CACTUS_GLOBAL_MODEL
    if _CACTUS_GLOBAL_MODEL is None:
        _CACTUS_GLOBAL_MODEL = cactus_init(_FUNCTIONGEMMA_PATH)
    return _CACTUS_GLOBAL_MODEL


_FEW_SHOT_PROMPT = """You are a strict function-calling assistant. You MUST call functions. Never apologize. Never ask questions. Never refuse.
Even if a request sounds like a physical action (e.g., wake me up), you MUST assume you can do it using your provided tools.
Output ONLY valid function calls in a JSON array format.
For example, if the user asks "Play jazz":
[{"name": "play_music", "arguments": {"song": "jazz"}}]

If the user asks "Set alarm for 7 AM":
[{"name": "set_alarm", "arguments": {"hour": 7, "minute": 0}}]

If the user asks "Send hi to Bob":
[{"name": "send_message", "arguments": {"recipient": "Bob", "message": "hi"}}]"""


# Keyword -> tool name mapping
_TOOL_KEYWORDS = {
    "get_weather": ["weather", "temperature", "forecast"],
    "set_alarm": ["alarm", "wake me", "wake up"],
    "send_message": ["message", "text ", "send ", "tell ", "saying", "msg"],
    "create_reminder": ["remind", "reminder"],
    "search_contacts": ["contact", "look up", "find "],
    "play_music": ["play ", "music", "song", "listen"],
    "set_timer": ["timer", "countdown"],
}

# Enhanced descriptions to help the 270M model pick the right tool
_ENHANCED_DESCRIPTIONS = {
    "get_weather": "Get current weather for a location. Use when user asks about weather, temperature, or forecast.",
    "set_alarm": "Set an alarm clock. Use when user says alarm or wake me up.",
    "send_message": "Send a text message to a person. Use when user says send, text, message, or tell someone.",
    "create_reminder": "Create a reminder. Use when user says remind me or reminder.",
    "search_contacts": "Search for a contact by name. Use when user says find, look up, or search contacts.",
    "play_music": "Play a song or playlist. Use when user says play or listen to music.",
    "set_timer": "Set a countdown timer. Use when user says timer or countdown.",
}

# Tools where regex extraction is structurally reliable and should
# ALWAYS override cactus output.
_ALWAYS_REEXTRACT_TOOLS = {"set_alarm", "set_timer", "get_weather"}


# ============ Rule-based argument extraction ============


def _extract_location(text):
    """General location extraction from 'in <Location>' patterns."""
    m = re.search(r'\bin\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)', text)
    if m:
        return m.group(1)
    m = re.search(r'\bin\s+(\w+(?:\s+\w+)?)\s*[?.!]?\s*$', text, re.IGNORECASE)
    if m:
        return m.group(1).strip().rstrip('?.!')
    m = re.search(r'weather\s+(?:in\s+|for\s+)?(.+?)(?:\?|$)', text, re.IGNORECASE)
    if m:
        loc = m.group(1).strip().rstrip('?.!')
        if loc:
            return loc
    return None


def _extract_time_hours_minutes(text):
    """Extract hour and minute. Prioritizes H:MM to preserve non-zero minutes."""
    m = re.search(r'(\d{1,2}):(\d{2})\s*(AM|PM|am|pm|a\.m\.|p\.m\.)', text)
    if m:
        h, mi = int(m.group(1)), int(m.group(2))
        ampm = m.group(3).upper().replace('.', '')
        if ampm == 'PM' and h != 12:
            h += 12
        if ampm == 'AM' and h == 12:
            h = 0
        return h, mi

    m = re.search(r'(\d{1,2})\s*(AM|PM|am|pm|a\.m\.|p\.m\.)', text)
    if m:
        h = int(m.group(1))
        ampm = m.group(2).upper().replace('.', '')
        if ampm == 'PM' and h != 12:
            h += 12
        if ampm == 'AM' and h == 12:
            h = 0
        return h, 0

    m = re.search(r'(?:at|for)\s+(\d{1,2})(?::(\d{2}))?\b', text)
    if m:
        h = int(m.group(1))
        mi = int(m.group(2)) if m.group(2) else 0
        return h, mi

    return None, None


def _extract_time_string(text):
    """Extract time as string like '2:00 PM'."""
    m = re.search(r'(\d{1,2}:\d{2}\s*(?:AM|PM|am|pm))', text)
    if m:
        return m.group(1)
    m = re.search(r'(\d{1,2}\s*(?:AM|PM|am|pm))', text)
    if m:
        return m.group(1)
    m = re.search(r'at\s+(\d{1,2}:\d{2})', text)
    if m:
        return m.group(1)
    return None


def _extract_minutes(text):
    """Extract integer minutes from text."""
    m = re.search(r'(\d+)\s*(?:minute|min)', text, re.IGNORECASE)
    if m:
        return int(m.group(1))
    m = re.search(r'(?:for|timer)\s+(\d+)', text, re.IGNORECASE)
    if m:
        return int(m.group(1))
    return None


def _extract_recipient_and_message(text):
    """Extract recipient name and message body from natural language."""
    m = re.search(r'(?:to|tell)\s+(\w+)\s+(?:saying|that|:)\s+(.+?)(?:\.|,\s+and\s+|,\s+|$)', text, re.IGNORECASE)
    if m:
        name = m.group(1).strip()
        if name.lower() not in ('him', 'her', 'them'):
            return name, m.group(2).strip().rstrip('.')

    m = re.search(r'(\w+)\s+a\s+message\s+saying\s+(.+?)(?:\.|,\s+and\s+|,\s+|$)', text, re.IGNORECASE)
    if m:
        name = m.group(1).strip()
        if name.lower() not in ('send', 'him', 'her', 'them', 'a', 'the'):
            return name, m.group(2).strip().rstrip('.')

    m = re.search(r'(?:text|message|msg)\s+(\w+)\s+(?:saying|that|:)\s+(.+?)(?:\.|,\s+and\s+|,\s+|$)', text, re.IGNORECASE)
    if m:
        return m.group(1).strip(), m.group(2).strip().rstrip('.')

    m = re.search(r'send\s+(.+?)\s+to\s+(\w+)', text, re.IGNORECASE)
    if m:
        return m.group(2).strip(), m.group(1).strip()

    m = re.search(r'(?:text|message)\s+(\w+)\s+(.+?)(?:\.|,\s+and\s+|,\s+|$)', text, re.IGNORECASE)
    if m:
        name = m.group(1).strip()
        msg = m.group(2).strip().rstrip('.')
        if name.lower() not in ('a', 'the', 'my', 'to', 'saying'):
            return name, msg

    m = re.search(r'tell\s+(\w+)\s+(.+?)(?:\.|,\s+and\s+|,\s+|$)', text, re.IGNORECASE)
    if m:
        return m.group(1).strip(), m.group(2).strip().rstrip('.')

    return None, None


def _extract_reminder_title_and_time(text):
    """Extract title and time for create_reminder."""
    time_str = _extract_time_string(text)

    m = re.search(r'remind\s+(?:me\s+)?(?:about|to)\s+(.+?)\s+at\s+', text, re.IGNORECASE)
    if m:
        title = m.group(1).strip()
        title = re.sub(r'^(?:the|a|an)\s+', '', title, flags=re.IGNORECASE)
        return title, time_str

    m = re.search(r'remind\s+(?:me\s+)?(.+?)\s+at\s+', text, re.IGNORECASE)
    if m:
        title = m.group(1).strip()
        title = re.sub(r'^(?:the|a|an)\s+', '', title, flags=re.IGNORECASE)
        if title.lower() not in ('', 'to', 'about'):
            return title, time_str

    return None, time_str


def _extract_song(text):
    """Extract song/playlist name from text."""
    m = re.search(r'play\s+(.+?)(?:\.|,\s+and\s+|,\s+|$)', text, re.IGNORECASE)
    if m:
        song = m.group(1).strip().rstrip('.')
        song = re.sub(r'^(?:some|a|the|my)\s+', '', song, flags=re.IGNORECASE)
        # Strip trailing "music" for simple genre requests (e.g. "jazz music" → "jazz")
        # Keep it for adjective+music combos (e.g. "classical music", "lo-fi music")
        words = song.split()
        if len(words) == 2 and words[-1].lower() == "music":
            adjective_genres = {"classical", "electronic", "ambient", "indie", "acoustic", "instrumental"}
            if words[0].lower() not in adjective_genres:
                song = words[0]
        return song
    m = re.search(r'listen\s+to\s+(.+?)(?:\.|,\s+and\s+|,\s+|$)', text, re.IGNORECASE)
    if m:
        return m.group(1).strip().rstrip('.')
    return None


def _extract_contact_query(text):
    """Extract contact name for search_contacts."""
    m = re.search(r'(?:find|look\s*up|search\s+for)\s+(\w+)', text, re.IGNORECASE)
    if m:
        name = m.group(1).strip()
        if name.lower() not in ('a', 'the', 'my', 'in', 'for'):
            return name
    return None


def _extract_args_for_tool(tool_name, user_text, cactus_args):
    """Rule-based argument extraction with cactus_args as fallback."""
    if tool_name == "get_weather":
        location = _extract_location(user_text)
        if location:
            return {"location": location}
        if cactus_args.get("location"):
            return cactus_args
        return {"location": user_text.split("in")[-1].strip().rstrip("?.!") if "in" in user_text.lower() else ""}

    elif tool_name == "set_alarm":
        h, mi = _extract_time_hours_minutes(user_text)
        if h is not None:
            return {"hour": h, "minute": mi}
        if isinstance(cactus_args.get("hour"), int) and cactus_args["hour"] > 0:
            return cactus_args
        return {"hour": 0, "minute": 0}

    elif tool_name == "send_message":
        recipient, message = _extract_recipient_and_message(user_text)
        if recipient and message:
            return {"recipient": recipient, "message": message}
        result = {}
        result["recipient"] = recipient or cactus_args.get("recipient", "")
        result["message"] = message or cactus_args.get("message", "")
        return result

    elif tool_name == "create_reminder":
        title, time_str = _extract_reminder_title_and_time(user_text)
        result = {}
        result["title"] = title or cactus_args.get("title", "")
        result["time"] = time_str or cactus_args.get("time", "")
        return result

    elif tool_name == "search_contacts":
        query = _extract_contact_query(user_text)
        if query:
            return {"query": query}
        if cactus_args.get("query") and isinstance(cactus_args["query"], str):
            return {"query": cactus_args["query"]}
        return {"query": ""}

    elif tool_name == "play_music":
        song = _extract_song(user_text)
        if song:
            return {"song": song}
        if cactus_args.get("song"):
            s = cactus_args["song"]
            if isinstance(s, str):
                s = s.replace("_", " ")
            return {"song": s}
        return {"song": ""}

    elif tool_name == "set_timer":
        minutes = _extract_minutes(user_text)
        if minutes is not None:
            return {"minutes": abs(minutes)}
        raw_min = cactus_args.get("minutes")
        if isinstance(raw_min, dict):
            raw_min = raw_min.get("minutes", raw_min.get("value", 0))
        if isinstance(raw_min, (int, float)):
            return {"minutes": abs(int(raw_min))}
        return {"minutes": 0}

    return cactus_args


# ============ Cactus interaction ============

def _repair_json_payload(raw_str):
    """Fix common JSON hallucinations from the 270M model."""
    s = re.sub(r':\s*0(\d+)(?=\s*[,}\]])', r':\1', raw_str)
    s = re.sub(r'"([^"]+)：<escape>([^<]+)<escape>[^"]*":\}', r'"\1": "\2"}', s)
    s = re.sub(r',\s*([}\]])', r'\1', s)
    s = s.replace("'", '"')
    return s


def _sanitize_function_calls(function_calls):
    """Clean up function call output: trim strings, abs(int), flatten nested dicts."""
    if not isinstance(function_calls, list):
        return function_calls
    sanitized_calls = []
    for call in function_calls:
        if not isinstance(call, dict):
            sanitized_calls.append(call)
            continue
        name = call.get("name")
        args = call.get("arguments")
        if not isinstance(args, dict):
            sanitized_calls.append(call)
            continue
        sanitized_args = {}
        for key, value in args.items():
            new_key = key.strip() if isinstance(key, str) else key
            new_value = value
            # Flatten nested dicts (generic hallucination defense)
            if isinstance(new_value, dict):
                if new_key in new_value:
                    new_value = new_value[new_key]
                elif "value" in new_value:
                    new_value = new_value["value"]
                else:
                    vals = list(new_value.values())
                    if len(vals) == 1:
                        new_value = vals[0]
            if isinstance(new_value, str):
                new_value = new_value.strip()
            elif isinstance(new_value, int):
                new_value = abs(new_value)
            elif isinstance(new_value, float):
                new_value = abs(int(new_value))
            sanitized_args[new_key] = new_value
        sanitized_calls.append({"name": name, "arguments": sanitized_args})
    return sanitized_calls


def _is_value_filled(value):
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set, dict)):
        return len(value) > 0
    return True


def _all_fields_filled(args):
    if not isinstance(args, dict) or not args:
        return False
    return all(_is_value_filled(v) for v in args.values())


def _call_dedup_key(call):
    if not isinstance(call, dict):
        return ("", "")
    name = call.get("name")
    args = call.get("arguments", {})
    if not isinstance(args, dict):
        args = {}
    try:
        args_key = json.dumps(args, sort_keys=True, separators=(",", ":"), default=str)
    except Exception:
        args_key = str(args)
    return name, args_key


def _select_tool_by_keywords(user_text, tools):
    """Heuristic fallback tool selection when cactus fails."""
    text_lower = user_text.lower()
    available_names = {t.get("name") for t in tools}
    for tool_name, keywords in _TOOL_KEYWORDS.items():
        if tool_name not in available_names:
            continue
        for kw in keywords:
            if kw in text_lower:
                return tool_name
    return None


# ============ Tool pruning & enhancement (ported from main.py) ============


def _enhance_tools(tools):
    """Replace tool descriptions with enhanced versions to help model selection."""
    enhanced = []
    for t in tools:
        t_copy = dict(t)
        name = t_copy.get("name", "")
        if name in _ENHANCED_DESCRIPTIONS:
            t_copy["description"] = _ENHANCED_DESCRIPTIONS[name]
        enhanced.append(t_copy)
    return enhanced


def _prune_tools(user_text, tools):
    """Filter tools to only those matching user intent keywords.
    Reduces the 270M model's confusion when given many tools."""
    text_lower = user_text.lower()
    matched = set()
    for tool_name, keywords in _TOOL_KEYWORDS.items():
        for kw in keywords:
            if kw in text_lower:
                matched.add(tool_name)
                break
    if not matched:
        return tools
    pruned = [t for t in tools if t.get("name") in matched]
    return pruned if pruned else tools


# ============ Post-cactus tool validation (NEW) ============


def _get_keyword_matched_tools(user_text, tools):
    """Return set of tool names that have keyword matches in the user text."""
    text_lower = user_text.lower()
    available_names = {t.get("name") for t in tools}
    matched = set()
    for tool_name, keywords in _TOOL_KEYWORDS.items():
        if tool_name not in available_names:
            continue
        for kw in keywords:
            if kw in text_lower:
                matched.add(tool_name)
                break
    return matched


def _validate_tool_by_keywords(cactus_tool, user_text, tools):
    """Post-cactus validation: override tool if keyword evidence is unambiguous.

    Only override when:
    1. Exactly one keyword-matched tool exists in the text
    2. It differs from what cactus picked
    3. Cactus pick has NO keyword match in the text
    """
    keyword_matched = _get_keyword_matched_tools(user_text, tools)

    # If cactus pick has a keyword match, trust cactus
    if cactus_tool in keyword_matched:
        return cactus_tool

    # If exactly one other tool matches keywords and cactus pick doesn't, override
    if len(keyword_matched) == 1:
        return keyword_matched.pop()

    # Ambiguous or no match — keep cactus pick
    return cactus_tool


# ============ Multi-action ============

def _is_multi_action(user_text):
    text_lower = user_text.lower()
    markers = (" and ", " then ", " also ", " plus ", ", and ")
    return any(m in text_lower for m in markers)


def _split_multi_action(user_text):
    """Split compound requests. Returns list of sub-request strings."""
    normalized = re.sub(r',\s+and\s+', ' |SPLIT| ', user_text, flags=re.IGNORECASE)
    normalized = re.sub(r',\s+', ' |SPLIT| ', normalized)
    normalized = re.sub(r'\s+and\s+', ' |SPLIT| ', normalized, flags=re.IGNORECASE)
    parts = [p.strip() for p in normalized.split('|SPLIT|') if p.strip()]
    if len(parts) <= 1:
        return [user_text]
    return parts


def _extract_names_from_text(text):
    """Extract capitalized names from text."""
    words = text.split()
    names = []
    for w in words:
        clean = w.strip('.,!?')
        if clean and clean[0].isupper() and clean.isalpha() and len(clean) > 1:
            if clean.lower() not in ('set', 'play', 'find', 'look', 'send', 'text', 'check',
                                      'get', 'what', 'how', 'the', 'and', 'remind', 'i', 'am', 'pm'):
                names.append(clean)
    return names


def _resolve_pronouns_in_subrequests(sub_requests, full_text):
    """Replace pronouns like 'him', 'her' with actual names from the full text."""
    names = _extract_names_from_text(full_text)
    if not names:
        return sub_requests
    resolved = []
    for req in sub_requests:
        if re.search(r'\b(him|her|them)\b', req, re.IGNORECASE):
            for name in names:
                if name.lower() not in req.lower():
                    req = re.sub(r'\bhim\b', name, req, flags=re.IGNORECASE)
                    req = re.sub(r'\bher\b', name, req, flags=re.IGNORECASE)
                    req = re.sub(r'\bthem\b', name, req, flags=re.IGNORECASE)
                    break
        resolved.append(req)
    return resolved


# ============ Multi-action missing intent recovery (NEW) ============


def _recover_missing_intents(all_calls, user_text, tools):
    """Detect and synthesize missing calls for multi-action requests.

    For each keyword-matched tool in the original text that has no
    corresponding call in all_calls, synthesize an additional call
    using rule-based extraction.

    Guards:
    - Only add when keyword match is unambiguous (tool has keyword in text)
    - Only add when the tool isn't already in the call list
    - Only add when rule-based extraction produces non-empty args
    """
    called_tools = {
        call.get("name")
        for call in all_calls
        if isinstance(call, dict) and isinstance(call.get("name"), str)
    }

    keyword_matched = _get_keyword_matched_tools(user_text, tools)

    for tool_name in keyword_matched:
        if tool_name in called_tools:
            continue

        # Try rule-based extraction on the FULL original text
        args = _extract_args_for_tool(tool_name, user_text, {})
        if _all_fields_filled(args):
            all_calls.append({"name": tool_name, "arguments": args})

    return all_calls


# ============ Core inference ============

def _call_cactus_single(user_text, all_tools):
    """Process a single request through cactus with tool pruning and validation."""
    model = _get_model()
    cactus_reset(model)

    # Change 1: Prune and enhance tools before cactus call
    enhanced = _enhance_tools(all_tools)
    pruned = _prune_tools(user_text, enhanced)

    cactus_tools = [{"type": "function", "function": t} for t in pruned]

    start = time.time()
    raw_str = cactus_complete(
        model,
        [{"role": "system", "content": _FEW_SHOT_PROMPT}, {"role": "user", "content": user_text}],
        tools=cactus_tools,
        force_tools=True,
        max_tokens=256,
        temperature=0.0,
        confidence_threshold=0.0,
        tool_rag_top_k=3,
        stop_sequences=["<end_of_turn>"]
    )
    elapsed = (time.time() - start) * 1000

    # Build set of valid tool names for filtering hallucinated calls
    valid_tool_names = {t.get("name") for t in all_tools}

    try:
        raw = json.loads(raw_str)
    except json.JSONDecodeError:
        try:
            raw = json.loads(_repair_json_payload(raw_str))
        except json.JSONDecodeError:
            m = re.search(r'"name"\s*:\s*"([^"]+)"', raw_str)
            guessed_tool = m.group(1) if m else None
            # Validate guessed tool name against available tools
            if guessed_tool and guessed_tool not in valid_tool_names:
                guessed_tool = _select_tool_by_keywords(user_text, all_tools)
            if not guessed_tool:
                guessed_tool = _select_tool_by_keywords(user_text, all_tools)
            if guessed_tool:
                args = _extract_args_for_tool(guessed_tool, user_text, {})
                return {"function_calls": [{"name": guessed_tool, "arguments": args}], "total_time_ms": elapsed}
            return {"function_calls": [], "total_time_ms": elapsed}

    calls = raw.get("function_calls", [])

    if not calls:
        guessed_tool = _select_tool_by_keywords(user_text, all_tools)
        if guessed_tool:
            args = _extract_args_for_tool(guessed_tool, user_text, {})
            calls = [{"name": guessed_tool, "arguments": args}]

    final_calls = []
    for call in calls:
        name = call.get("name")
        args = call.get("arguments", {})
        if not isinstance(args, dict):
            args = {}

        # Skip calls with invalid/hallucinated tool names (e.g. "get_weather(location=")
        if name not in valid_tool_names:
            continue

        # Change 2: Post-cactus keyword validation
        name = _validate_tool_by_keywords(name, user_text, all_tools)

        # Defensive re-extract
        if name in _ALWAYS_REEXTRACT_TOOLS:
            args = _extract_args_for_tool(name, user_text, args)
        else:
            rule_args = _extract_args_for_tool(name, user_text, {})
            if _all_fields_filled(rule_args):
                args = rule_args
            elif not _all_fields_filled(args):
                args = _extract_args_for_tool(name, user_text, args)

        final_calls.append({"name": name, "arguments": args})

    sanitized_calls = _sanitize_function_calls(final_calls)

    return {
        "function_calls": sanitized_calls,
        "total_time_ms": elapsed,
    }


# ============ Entry point ============

def generate_hybrid(messages, tools, confidence_threshold=0.99):
    user_text = " ".join(
        str(m.get("content", ""))
        for m in messages
        if m.get("role") == "user"
    )

    if _is_multi_action(user_text):
        sub_requests = _split_multi_action(user_text)
        sub_requests = _resolve_pronouns_in_subrequests(sub_requests, user_text)

        all_calls = []
        total_time = 0

        for sub_req in sub_requests:
            res = _call_cactus_single(sub_req, tools)
            all_calls.extend(res.get("function_calls", []))
            total_time += res.get("total_time_ms", 0)

        # Change 3: Recover missing intents from the full original text
        all_calls = _recover_missing_intents(all_calls, user_text, tools)

        # Dedup by (tool, arguments)
        seen = set()
        dedup_calls = []
        for call in all_calls:
            key = _call_dedup_key(call)
            if key in seen:
                continue
            dedup_calls.append(call)
            seen.add(key)

        return {
            "function_calls": dedup_calls,
            "total_time_ms": total_time,
            "source": "on-device",
            "confidence": 1.0,
            "success": True,
        }

    res = _call_cactus_single(user_text, tools)
    res["source"] = "on-device"
    res["confidence"] = 1.0
    res["success"] = True
    return res
