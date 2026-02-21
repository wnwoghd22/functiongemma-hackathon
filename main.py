"""On-device only strategy v3.1: Hybrid cactus + rule-based extraction.

Server cloud fallback doesn't work → on-device 100%.
Key insight: The 270M model is good at tool SELECTION but bad at argument EXTRACTION.
Strategy: Use cactus to pick the right tool, then extract arguments with rules.

Techniques:
1. Tool pruning: keyword-based filtering to reduce confusion
2. Multi-action splitting: split compound requests
3. Rule-based argument extraction from user text
4. Cactus as tool selector + fallback for argument values
5. Parse response field when function_calls is empty
"""

import json
import os
import re
import sys
import time
import requests

sys.path.insert(0, "cactus/python/src")
from cactus import cactus_init, cactus_complete, cactus_destroy, cactus_reset

try:
    from google import genai
    from google.genai import types
except Exception:
    genai = None
    types = None

_FUNCTIONGEMMA_PATH = "cactus/weights/functiongemma-270m-it"
_CACTUS_GLOBAL_MODEL = None
# Submission-safe fixed routing knobs (do not depend on local shell env).
_CLOUD_FALLBACK_TOOL_THRESHOLD = 5
_ENABLE_AGGRESSIVE_FALLBACK = False
_ALWAYS_REEXTRACT_TOOLS = {"set_alarm", "set_timer", "get_weather"}

_LOCAL_SYSTEM_PROMPT = (
    "You are a function-calling assistant. You MUST call functions. "
    "Never apologize. Never ask questions. Never refuse. "
    "Output ONLY valid function calls in JSON.\n"
    "Example: User: \"Play jazz\" → {\"name\": \"play_music\", \"arguments\": {\"song\": \"jazz\"}}\n"
    "Example: User: \"Set alarm for 7 AM\" → {\"name\": \"set_alarm\", \"arguments\": {\"hour\": 7, \"minute\": 0}}\n"
    "Example: User: \"Send hi to Bob\" → {\"name\": \"send_message\", \"arguments\": {\"recipient\": \"Bob\", \"message\": \"hi\"}}"
)

_FEW_SHOT_PROMPT = """You are a strict function-calling assistant. You MUST call functions. Never apologize. Never ask questions. Never refuse.
Even if a request sounds like a physical action (e.g., wake me up), you MUST assume you can do it using your provided tools.
Output ONLY valid function calls in a JSON array format.
For example, if the user asks "Play jazz":
[{"name": "play_music", "arguments": {"song": "jazz"}}]

If the user asks "Set alarm for 7 AM":
[{"name": "set_alarm", "arguments": {"hour": 7, "minute": 0}}]

If the user asks "Send hi to Bob":
[{"name": "send_message", "arguments": {"recipient": "Bob", "message": "hi"}}]"""

# Keyword → tool name mapping for tool pruning
_TOOL_KEYWORDS = {
    "get_weather": ["weather", "temperature", "forecast"],
    "set_alarm": ["alarm", "wake me", "wake up"],
    "send_message": ["message", "text ", "send ", "tell ", "saying", "msg"],
    "create_reminder": ["remind", "reminder"],
    "search_contacts": ["contact", "look up", "find "],
    "play_music": ["play ", "music", "song", "listen"],
    "set_timer": ["timer", "countdown"],
}

# Enhanced descriptions
_ENHANCED_DESCRIPTIONS = {
    "get_weather": "Get current weather for a location. Use when user asks about weather, temperature, or forecast.",
    "set_alarm": "Set an alarm clock. Use when user says alarm or wake me up.",
    "send_message": "Send a text message to a person. Use when user says send, text, message, or tell someone.",
    "create_reminder": "Create a reminder. Use when user says remind me or reminder.",
    "search_contacts": "Search for a contact by name. Use when user says find, look up, or search contacts.",
    "play_music": "Play a song or playlist. Use when user says play or listen to music.",
    "set_timer": "Set a countdown timer. Use when user says timer or countdown.",
}


# ============ Rule-based argument extraction ============

def _get_model():
    global _CACTUS_GLOBAL_MODEL
    if _CACTUS_GLOBAL_MODEL is None:
        _CACTUS_GLOBAL_MODEL = cactus_init(_FUNCTIONGEMMA_PATH)
    return _CACTUS_GLOBAL_MODEL

def _extract_location(text):
    """Extract location from text like 'weather in San Francisco'."""
    # "in <Location>" pattern
    m = re.search(r'\bin\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)', text)
    if m:
        return m.group(1)
    # "in <location>" case-insensitive fallback
    m = re.search(r'\bin\s+(\w+(?:\s+\w+)?)\s*[?.!]?\s*$', text, re.IGNORECASE)
    if m:
        return m.group(1).strip().rstrip('?.!')
    # "weather <location>" pattern
    m = re.search(r'weather\s+(?:in\s+|for\s+)?(.+?)(?:\?|$)', text, re.IGNORECASE)
    if m:
        loc = m.group(1).strip().rstrip('?.!')
        if loc:
            return loc
    return None


def _extract_time_hours_minutes(text):
    """Extract hour and minute from text like '7:30 AM' or '6 AM'."""
    # "H:MM AM/PM"
    m = re.search(r'(\d{1,2}):(\d{2})\s*(AM|PM|am|pm|a\.m\.|p\.m\.)', text)
    if m:
        h, mi, ampm = int(m.group(1)), int(m.group(2)), m.group(3).upper().replace('.', '')
        if ampm == 'PM' and h != 12:
            h += 12
        if ampm == 'AM' and h == 12:
            h = 0
        return h, mi

    # "H AM/PM"
    m = re.search(r'(\d{1,2})\s*(AM|PM|am|pm|a\.m\.|p\.m\.)', text)
    if m:
        h, ampm = int(m.group(1)), m.group(2).upper().replace('.', '')
        if ampm == 'PM' and h != 12:
            h += 12
        if ampm == 'AM' and h == 12:
            h = 0
        return h, 0

    # Just a number after "at" or "for"
    m = re.search(r'(?:at|for)\s+(\d{1,2})(?::(\d{2}))?\b', text)
    if m:
        h = int(m.group(1))
        mi = int(m.group(2)) if m.group(2) else 0
        return h, mi

    return None, None


def _extract_time_string(text):
    """Extract time as a string like '3:00 PM' from text."""
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
    """Extract number of minutes from text."""
    m = re.search(r'(\d+)\s*(?:minute|min)', text, re.IGNORECASE)
    if m:
        return int(m.group(1))
    m = re.search(r'(?:for|timer)\s+(\d+)', text, re.IGNORECASE)
    if m:
        return int(m.group(1))
    return None


def _extract_recipient_and_message(text):
    """Extract recipient and message from text like 'Send a message to Alice saying good morning'."""
    # "to <Name> saying <message>"
    m = re.search(r'(?:to|tell)\s+(\w+)\s+(?:saying|that|:)\s+(.+?)(?:\.|$)', text, re.IGNORECASE)
    if m:
        name = m.group(1).strip()
        if name.lower() not in ('him', 'her', 'them'):
            return name, m.group(2).strip().rstrip('.')

    # "<Name> a message saying <message>"
    m = re.search(r'(\w+)\s+a\s+message\s+saying\s+(.+?)(?:\.|$)', text, re.IGNORECASE)
    if m:
        name = m.group(1).strip()
        if name.lower() not in ('send', 'him', 'her', 'them', 'a', 'the'):
            return name, m.group(2).strip().rstrip('.')

    # "<verb> <Name> saying <message>"
    m = re.search(r'(?:text|message|msg)\s+(\w+)\s+(?:saying|that|:)\s+(.+?)(?:\.|$)', text, re.IGNORECASE)
    if m:
        return m.group(1).strip(), m.group(2).strip().rstrip('.')

    # "send <message> to <Name>"
    m = re.search(r'send\s+(.+?)\s+to\s+(\w+)', text, re.IGNORECASE)
    if m:
        return m.group(2).strip(), m.group(1).strip()

    # "text <Name> <message>" (no "saying")
    m = re.search(r'(?:text|message)\s+(\w+)\s+(.+?)(?:\.|$)', text, re.IGNORECASE)
    if m:
        name = m.group(1).strip()
        msg = m.group(2).strip().rstrip('.')
        # Filter out common non-name words
        if name.lower() not in ('a', 'the', 'my', 'to', 'saying'):
            return name, msg

    # "send a message to <Name> saying <msg>"  (broader)
    m = re.search(r'to\s+(\w+)\s+saying\s+(.+?)(?:\.|$)', text, re.IGNORECASE)
    if m:
        return m.group(1).strip(), m.group(2).strip().rstrip('.')

    # "tell <Name> <message>"
    m = re.search(r'tell\s+(\w+)\s+(.+?)(?:\.|$)', text, re.IGNORECASE)
    if m:
        return m.group(1).strip(), m.group(2).strip().rstrip('.')

    return None, None


def _extract_reminder_title_and_time(text):
    """Extract reminder title and time from text."""
    time_str = _extract_time_string(text)

    # "remind me about/to <title> at <time>"
    m = re.search(r'remind\s+(?:me\s+)?(?:about|to)\s+(.+?)\s+at\s+', text, re.IGNORECASE)
    if m:
        title = m.group(1).strip()
        # Strip leading articles
        title = re.sub(r'^(?:the|a|an)\s+', '', title, flags=re.IGNORECASE)
        return title, time_str

    # "remind me <title> at <time>"
    m = re.search(r'remind\s+(?:me\s+)?(.+?)\s+at\s+', text, re.IGNORECASE)
    if m:
        title = m.group(1).strip()
        title = re.sub(r'^(?:the|a|an)\s+', '', title, flags=re.IGNORECASE)
        if title.lower() not in ('', 'to', 'about'):
            return title, time_str

    return None, time_str


def _extract_song(text):
    """Extract song/playlist name from text."""
    # "play <song>"
    m = re.search(r'play\s+(.+?)(?:\.|$)', text, re.IGNORECASE)
    if m:
        song = m.group(1).strip().rstrip('.')
        # Remove filler words
        song = re.sub(r'^(?:some|a|the|my)\s+', '', song, flags=re.IGNORECASE)
        # Strip trailing "music" only for single-word genres (e.g. "jazz music" → "jazz")
        # Keep it for multi-word or adjective+music combos (e.g. "classical music", "lo-fi music")
        words = song.split()
        if len(words) == 2 and words[-1].lower() == "music":
            # Only strip if the first word is a standalone genre name, not an adjective
            adjective_genres = {"classical", "electronic", "ambient", "indie", "acoustic", "instrumental"}
            if words[0].lower() not in adjective_genres:
                song = words[0]
        return song
    # "listen to <song>"
    m = re.search(r'listen\s+to\s+(.+?)(?:\.|$)', text, re.IGNORECASE)
    if m:
        return m.group(1).strip().rstrip('.')
    return None


def _extract_contact_query(text):
    """Extract contact name from text."""
    # "find <Name> in my contacts"
    m = re.search(r'(?:find|look\s*up|search\s+for)\s+(\w+)', text, re.IGNORECASE)
    if m:
        name = m.group(1).strip()
        if name.lower() not in ('a', 'the', 'my', 'in', 'for'):
            return name
    return None


def _extract_args_for_tool(tool_name, user_text, cactus_args):
    """Extract arguments using rules, falling back to cactus output."""
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
        if cactus_args.get("query"):
            return cactus_args
        return {"query": ""}

    elif tool_name == "play_music":
        song = _extract_song(user_text)
        if song:
            return {"song": song}
        if cactus_args.get("song"):
            s = cactus_args["song"].replace("_", " ")
            return {"song": s}
        return {"song": ""}

    elif tool_name == "set_timer":
        minutes = _extract_minutes(user_text)
        if minutes is not None:
            return {"minutes": abs(minutes)}
        if isinstance(cactus_args.get("minutes"), (int, float)):
            return {"minutes": abs(int(cactus_args["minutes"]))}
        return {"minutes": 0}

    # Unknown tool: use cactus args as-is
    return cactus_args


# ============ Cactus interaction ============

def _repair_json_payload(raw_str):
    s = re.sub(r':\s*0(\d+)(?=\s*[,}\]])', r':\1', raw_str)
    s = re.sub(r'"([^"]+)：<escape>([^<]+)<escape>[^"]*":\}', r'"\1": "\2"}', s)
    s = re.sub(r',\s*([}\]])', r'\1', s)
    s = s.replace("'", '"')
    return s


def _sanitize_string_value(value):
    return value.strip()


def _sanitize_function_calls(function_calls):
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
            if isinstance(new_value, str):
                new_value = _sanitize_string_value(new_value)
            elif isinstance(new_value, int):
                new_value = abs(new_value)
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


def _enhance_tools(tools):
    enhanced = []
    for t in tools:
        t_copy = dict(t)
        name = t_copy.get("name", "")
        if name in _ENHANCED_DESCRIPTIONS:
            t_copy["description"] = _ENHANCED_DESCRIPTIONS[name]
        enhanced.append(t_copy)
    return enhanced


def _prune_tools(user_text, tools):
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


def _call_cactus(messages, tools):
    model = cactus_init(_FUNCTIONGEMMA_PATH)
    cactus_tools = [{"type": "function", "function": t} for t in tools]
    raw_str = cactus_complete(
        model,
        [{"role": "system", "content": _LOCAL_SYSTEM_PROMPT}] + messages,
        tools=cactus_tools,
        force_tools=True,
        max_tokens=512,
        temperature=0.2,
        confidence_threshold=0.0,
        tool_rag_top_k=0,
        stop_sequences=["<end_of_turn>"],
    )
    cactus_destroy(model)
    return raw_str


def _parse_tool_name_from_response(response_text, available_tools):
    """Try to extract a tool name from the response text when function_calls is empty."""
    available_names = {t.get("name") for t in available_tools}
    for name in available_names:
        if name in response_text:
            return name
    # Try "call:<tool_name>" pattern
    m = re.search(r'call[:\s]+(\w+)', response_text)
    if m and m.group(1) in available_names:
        return m.group(1)
    return None


def _parse_cactus_output(raw_str, tools):
    """Parse cactus output, including from response field."""
    try:
        raw = json.loads(raw_str)
    except json.JSONDecodeError:
        try:
            raw = json.loads(_repair_json_payload(raw_str))
        except json.JSONDecodeError:
            return None

    calls = raw.get("function_calls", [])

    # If function_calls is empty but response has content, try to parse tool name from response
    if not calls and raw.get("response"):
        tool_name = _parse_tool_name_from_response(raw["response"], tools)
        if tool_name:
            calls = [{"name": tool_name, "arguments": {}}]

    return {
        "function_calls": calls,
        "total_time_ms": raw.get("total_time_ms", 0),
    }


# ============ Tool selection heuristic ============

def _select_tool_by_keywords(user_text, tools):
    """Heuristic tool selection based on keywords when cactus fails."""
    text_lower = user_text.lower()
    available_names = {t.get("name") for t in tools}

    for tool_name, keywords in _TOOL_KEYWORDS.items():
        if tool_name not in available_names:
            continue
        for kw in keywords:
            if kw in text_lower:
                return tool_name
    return None


# ============ Multi-action ============

def _is_multi_action(user_text, tools=None):
    text_lower = user_text.lower()
    markers = (" and ", " then ", " also ", " plus ", ", and ")
    return any(m in text_lower for m in markers)


def _split_multi_action(user_text):
    """Split compound requests. Returns list of sub-request strings."""
    # First try combined comma + and splitting for patterns like "A, B, and C"
    # Replace ", and " with a unique delimiter first
    normalized = re.sub(r',\s+and\s+', ' |SPLIT| ', user_text, flags=re.IGNORECASE)
    # Then replace remaining ", "
    normalized = re.sub(r',\s+', ' |SPLIT| ', normalized)
    # Then replace remaining " and "
    normalized = re.sub(r'\s+and\s+', ' |SPLIT| ', normalized, flags=re.IGNORECASE)

    parts = [p.strip() for p in normalized.split('|SPLIT|') if p.strip()]
    if len(parts) <= 1:
        return [user_text]
    return parts


def _extract_names_from_text(text):
    """Extract capitalized names from text."""
    # Find capitalized words that look like names (not at sentence start)
    words = text.split()
    names = []
    for i, w in enumerate(words):
        clean = w.strip('.,!?')
        if clean and clean[0].isupper() and clean.isalpha() and len(clean) > 1:
            # Skip words at absolute start or common non-names
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
        # Check if this sub-request has a pronoun that needs resolving
        if re.search(r'\b(him|her|them)\b', req, re.IGNORECASE):
            # Find a name from the full text that's not in this sub-request
            for name in names:
                if name.lower() not in req.lower():
                    req = re.sub(r'\bhim\b', name, req, flags=re.IGNORECASE)
                    req = re.sub(r'\bher\b', name, req, flags=re.IGNORECASE)
                    req = re.sub(r'\bthem\b', name, req, flags=re.IGNORECASE)
                    break
        resolved.append(req)
    return resolved


# ============ Main entry point ============

def _process_single(user_text, tools):
    """Process a single (non-compound) request."""
    messages = [{"role": "user", "content": user_text}]
    enhanced = _enhance_tools(tools)
    pruned = _prune_tools(user_text, enhanced)

    raw_str = _call_cactus(messages, pruned)
    result = _parse_cactus_output(raw_str, pruned)

    total_time = result["total_time_ms"] if result else 0

    tool_name = None
    cactus_args = {}

    if result and result["function_calls"]:
        call = result["function_calls"][0]
        if isinstance(call, dict) and isinstance(call.get("name"), str):
            tool_name = call["name"]
            cactus_args = call.get("arguments", {})
            if not isinstance(cactus_args, dict):
                cactus_args = {}

    # If cactus didn't pick a tool, use keyword heuristic
    if not tool_name:
        tool_name = _select_tool_by_keywords(user_text, tools)

    if not tool_name:
        return {"function_calls": [], "total_time_ms": total_time}

    # Validate tool_name exists in available tools
    available_names = {t.get("name") for t in tools}
    if tool_name not in available_names:
        tool_name = _select_tool_by_keywords(user_text, tools)
        if not tool_name:
            return {"function_calls": [], "total_time_ms": total_time}

    # Extract arguments using rules (with cactus args as fallback)
    args = _extract_args_for_tool(tool_name, user_text, cactus_args)

    return {
        "function_calls": [{"name": tool_name, "arguments": args}],
        "total_time_ms": total_time,
    }


def _call_cactus_single(user_text, all_tools, confidence_threshold=0.0):
    model = _get_model()
    cactus_reset(model)
    cactus_tools = [{"type": "function", "function": t} for t in all_tools]

    start = time.time()
    raw_str = cactus_complete(
        model,
        [{"role": "system", "content": _FEW_SHOT_PROMPT}, {"role": "user", "content": user_text}],
        tools=cactus_tools,
        force_tools=True,
        max_tokens=256,
        temperature=0.0,
        confidence_threshold=confidence_threshold,
        tool_rag_top_k=3,
        stop_sequences=["<end_of_turn>"],
    )
    elapsed = (time.time() - start) * 1000

    cloud_handoff = False
    try:
        raw = json.loads(raw_str)
        cloud_handoff = raw.get("cloud_handoff", False)
    except json.JSONDecodeError:
        try:
            raw = json.loads(_repair_json_payload(raw_str))
            cloud_handoff = raw.get("cloud_handoff", False)
        except json.JSONDecodeError:
            m = re.search(r'"name"\s*:\s*"([^"]+)"', raw_str)
            guessed_tool = m.group(1) if m else _select_tool_by_keywords(user_text, all_tools)
            if guessed_tool:
                args = _extract_args_for_tool(guessed_tool, user_text, {})
                return {"function_calls": [{"name": guessed_tool, "arguments": args}], "total_time_ms": elapsed, "cloud_handoff": False}
            return {"function_calls": [], "total_time_ms": elapsed, "cloud_handoff": True}

    calls = raw.get("function_calls", [])
    if not calls:
        guessed_tool = _select_tool_by_keywords(user_text, all_tools)
        if guessed_tool:
            args = _extract_args_for_tool(guessed_tool, user_text, {})
            calls = [{"name": guessed_tool, "arguments": args}]

    final_calls = []
    for call in calls:
        if not isinstance(call, dict):
            continue

        name = call.get("name")
        args = call.get("arguments", {})
        if not isinstance(args, dict):
            args = {}

        # Defensive override:
        # - For structurally reliable tools, always prefer regex extraction.
        # - For others, only override when regex is complete or model args are empty/broken.
        if name in _ALWAYS_REEXTRACT_TOOLS:
            args = _extract_args_for_tool(name, user_text, args)
        else:
            rule_args = _extract_args_for_tool(name, user_text, {})
            if _all_fields_filled(rule_args):
                args = rule_args
            elif not _all_fields_filled(args):
                args = _extract_args_for_tool(name, user_text, args)

        final_calls.append({"name": name, "arguments": args})

    return {
        "function_calls": _sanitize_function_calls(final_calls),
        "total_time_ms": elapsed,
        "cloud_handoff": cloud_handoff,
    }


def _messages_to_user_text(messages):
    return " ".join(
        str(m.get("content", ""))
        for m in messages
        if m.get("role") == "user"
    )


def _should_fallback_to_cloud(local_result, messages, tools):
    calls = local_result.get("function_calls") or []
    tool_map = {t.get("name"): t for t in tools if t.get("name")}
    tool_names = set(tool_map.keys())

    if tools and not calls:
        return True, "empty_function_calls"

    if local_result.get("cloud_handoff"):
        return True, "low_confidence_handoff"

    for call in calls:
        if not isinstance(call, dict):
            return True, "invalid_call_shape"
        name = call.get("name")
        args = call.get("arguments")
        if not isinstance(name, str) or not name:
            return True, "invalid_call_name"
        if not isinstance(args, dict):
            return True, "invalid_arguments_shape"
        if tool_names and name not in tool_names:
            return True, "unknown_tool_name"

        schema = tool_map.get(name, {}).get("parameters", {})
        for req_key in schema.get("required", []):
            if req_key not in args:
                return True, "missing_required_argument"
            value = args.get(req_key)
            if value is None:
                return True, "null_required_argument"
            if isinstance(value, str) and not value.strip():
                return True, "empty_required_string"

    user_text = _messages_to_user_text(messages)
    user_text_lower = user_text.lower()
    called_tool_names = {
        call.get("name")
        for call in calls
        if isinstance(call, dict) and isinstance(call.get("name"), str)
    }

    if _is_multi_action(user_text) and len(calls) < 2:
        return True, "multi_action_under_called"

    # Narrow targeted fallback for known weak family:
    # reminder intent with many candidate tools but no reminder call selected.
    if (
        len(tools) >= 4
        and ("remind" in user_text_lower or "reminder" in user_text_lower)
        and "create_reminder" in tool_names
        and "create_reminder" not in called_tool_names
    ):
        return True, "reminder_intent_without_tool"

    # Narrow targeted fallback for alarm+reminder combined intents.
    has_alarm_intent = any(k in user_text_lower for k in ("alarm", "wake me", "wake up"))
    has_reminder_intent = "remind" in user_text_lower or "reminder" in user_text_lower
    if (
        _is_multi_action(user_text)
        and has_alarm_intent
        and has_reminder_intent
        and {"set_alarm", "create_reminder"}.issubset(tool_names)
        and not {"set_alarm", "create_reminder"}.issubset(called_tool_names)
    ):
        return True, "alarm_reminder_combo_incomplete"

    if _ENABLE_AGGRESSIVE_FALLBACK and len(tools) >= _CLOUD_FALLBACK_TOOL_THRESHOLD and len(calls) <= 1:
        return True, "many_tools_low_coverage"

    return False, "on_device_ok"


def _get_api_key():
    return os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")


def _map_schema_type(type_name):
    t = str(type_name or "string").lower()
    if t == "object":
        return "OBJECT"
    if t == "array":
        return "ARRAY"
    if t == "integer":
        return "INTEGER"
    if t == "number":
        return "NUMBER"
    if t == "boolean":
        return "BOOLEAN"
    return "STRING"


def _convert_schema_for_gemini(schema):
    schema = schema or {}
    converted = {"type": _map_schema_type(schema.get("type", "object"))}
    if "description" in schema:
        converted["description"] = schema["description"]
    if converted["type"] == "OBJECT":
        props = schema.get("properties", {})
        converted["properties"] = {
            key: _convert_schema_for_gemini(value)
            for key, value in props.items()
        }
        required = schema.get("required", [])
        if required:
            converted["required"] = required
    elif converted["type"] == "ARRAY" and "items" in schema:
        converted["items"] = _convert_schema_for_gemini(schema.get("items", {}))
    return converted


def _build_function_declarations(tools):
    return [
        {
            "name": t.get("name", ""),
            "description": t.get("description", ""),
            "parameters": _convert_schema_for_gemini(t.get("parameters", {})),
        }
        for t in tools
    ]


def _extract_calls_from_gemini_payload(payload):
    function_calls = []
    for candidate in payload.get("candidates", []):
        content = candidate.get("content", {})
        for part in content.get("parts", []):
            call = part.get("functionCall")
            if not call:
                continue
            args = call.get("args", {})
            if not isinstance(args, dict):
                args = {}
            function_calls.append({"name": call.get("name", ""), "arguments": args})
    return function_calls


def _generate_cloud_via_rest(messages, tools, model_name, api_key):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
    contents = [
        {"role": "user", "parts": [{"text": str(m.get("content", ""))}]}
        for m in messages
        if m.get("role") == "user"
    ]
    if not contents:
        contents = [{"role": "user", "parts": [{"text": _messages_to_user_text(messages)}]}]

    payload = {
        "contents": contents,
        "tools": [{"functionDeclarations": _build_function_declarations(tools)}],
        "generationConfig": {"temperature": 0.0},
    }

    start = time.time()
    resp = requests.post(url, params={"key": api_key}, json=payload, timeout=20)
    elapsed = (time.time() - start) * 1000
    if resp.status_code != 200:
        raise RuntimeError(f"cloud_rest_{resp.status_code}: {resp.text[:200]}")

    data = resp.json()
    return {"function_calls": _extract_calls_from_gemini_payload(data), "total_time_ms": elapsed}


def _generate_cloud_via_genai(messages, tools, model_name, api_key):
    if genai is None or types is None:
        raise RuntimeError("google.genai_not_available")

    client = genai.Client(api_key=api_key)
    declarations = []
    for t in tools:
        params = t.get("parameters", {})
        properties = params.get("properties", {})
        schema_properties = {}
        for key, value in properties.items():
            schema_properties[key] = types.Schema(
                type=_map_schema_type(value.get("type", "string")),
                description=value.get("description", ""),
            )
        declarations.append(
            types.FunctionDeclaration(
                name=t.get("name", ""),
                description=t.get("description", ""),
                parameters=types.Schema(
                    type="OBJECT",
                    properties=schema_properties,
                    required=params.get("required", []),
                ),
            )
        )

    contents = [
        str(m.get("content", ""))
        for m in messages
        if m.get("role") == "user"
    ]
    if not contents:
        contents = [_messages_to_user_text(messages)]

    start = time.time()
    resp = client.models.generate_content(
        model=model_name,
        contents=contents,
        config=types.GenerateContentConfig(
            tools=[types.Tool(function_declarations=declarations)]
        ),
    )
    elapsed = (time.time() - start) * 1000

    function_calls = []
    for candidate in (resp.candidates or []):
        content = getattr(candidate, "content", None)
        if not content or not getattr(content, "parts", None):
            continue
        for part in content.parts:
            if getattr(part, "function_call", None):
                args = dict(part.function_call.args) if part.function_call.args else {}
                function_calls.append({"name": part.function_call.name, "arguments": args})

    return {"function_calls": function_calls, "total_time_ms": elapsed}


def _generate_cloud(messages, tools):
    api_key = _get_api_key()
    if not api_key:
        raise RuntimeError("missing_api_key")

    # Keep cloud model fallback order deterministic across local/server runs.
    models_to_try = [
        "gemini-2.5-flash-lite",
        "gemini-2.5-flash",
        "gemini-1.5-flash",
    ]

    last_error = None
    for model_name in models_to_try:
        try:
            cloud = _generate_cloud_via_genai(messages, tools, model_name, api_key)
        except Exception as e_genai:
            try:
                cloud = _generate_cloud_via_rest(messages, tools, model_name, api_key)
            except Exception as e_rest:
                last_error = f"{model_name}: genai={e_genai}; rest={e_rest}"
                continue

        if cloud.get("function_calls"):
            cloud["cloud_model"] = model_name
            return cloud
        last_error = f"{model_name}: empty_function_calls"

    raise RuntimeError(last_error or "cloud_generation_failed")


def generate_hybrid(messages, tools, confidence_threshold=0.0):
    user_text = _messages_to_user_text(messages)

    if _is_multi_action(user_text):
        sub_requests = _split_multi_action(user_text)
        sub_requests = _resolve_pronouns_in_subrequests(sub_requests, user_text)

        all_calls = []
        total_time = 0
        needs_cloud_multi = False
        for sub_req in sub_requests:
            res = _call_cactus_single(sub_req, tools, confidence_threshold=confidence_threshold)
            all_calls.extend(res.get("function_calls", []))
            total_time += res.get("total_time_ms", 0)
            if res.get("cloud_handoff", False):
                needs_cloud_multi = True

        seen = set()
        dedup_calls = []
        for call in all_calls:
            key = _call_dedup_key(call)
            if key in seen:
                continue
            seen.add(key)
            dedup_calls.append(call)

        local = {
            "function_calls": dedup_calls,
            "total_time_ms": total_time,
            "source": "on-device",
            "confidence": 1.0,
            "success": True,
            "cloud_handoff": needs_cloud_multi,
        }
    else:
        local = _call_cactus_single(user_text, tools, confidence_threshold=confidence_threshold)
        local["source"] = "on-device"
        local["confidence"] = 1.0
        local["success"] = True

    needs_cloud, reason = _should_fallback_to_cloud(local, messages, tools)
    if not needs_cloud:
        local["fallback_reason"] = reason
        return local

    try:
        cloud = _generate_cloud(messages, tools)
        cloud["source"] = "cloud (fallback)"
        cloud["fallback_reason"] = reason
        cloud["local_time_ms"] = local.get("total_time_ms", 0)
        cloud["total_time_ms"] = cloud.get("total_time_ms", 0) + local.get("total_time_ms", 0)
        return cloud
    except Exception as e:
        local["fallback_reason"] = reason
        local["cloud_error"] = str(e)
        return local
