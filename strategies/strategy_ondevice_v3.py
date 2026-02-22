"""On-Device Strategy v3: Generalized with input normalization.

Built on v2 (defensive re-extract, no comma false-positive, tuple dedup).
Adds a pre-processing normalization layer to handle paraphrase diversity
identified in §45 overfitting stress test:

1. Time phrasing normalization:
   - "quarter past X" → "X:15"
   - "half past X" → "X:30"
   - "quarter to X" → "(X-1):45"
   - "half an hour"/"half hour" → "30 minutes"
   - "an hour" → "60 minutes"
   - "in the morning" → "AM", "in the evening"/"at night" → "PM"

2. Verb alias normalization:
   - "shoot/fire/ping/drop (someone) a text/message" → "send message to"
   - "hit up" → "send message to"

3. Weather phrasing normalization:
   - "outside in X" → "weather in X"
   - "how's it in X" → "weather in X"

4. Timer alias normalization:
   - "countdown" → "timer"
   - "set a countdown for" → "set a timer for"

5. Broader keyword table for tool selection fallback.

6. Broader regex patterns for recipient/message extraction.
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


# Keyword → tool name mapping (broader than v2)
_TOOL_KEYWORDS = {
    "get_weather": ["weather", "temperature", "forecast", "outside", "how's it"],
    "set_alarm": ["alarm", "wake me", "wake up"],
    "send_message": ["message", "text ", "send ", "tell ", "saying", "msg",
                      "shoot ", "ping ", "drop ", "hit up"],
    "create_reminder": ["remind", "reminder"],
    "search_contacts": ["contact", "look up", "find ", "phonebook"],
    "play_music": ["play ", "music", "song", "listen"],
    "set_timer": ["timer", "countdown"],
}

_ALWAYS_REEXTRACT_TOOLS = {"set_alarm", "set_timer", "get_weather"}


# ============ Input normalization (NEW in v3) ============

def _normalize_input(text):
    """Pre-process user text to normalize paraphrases into canonical forms.

    This runs BEFORE cactus inference and regex extraction to ensure both
    the model and the rule engine see standardized phrasing.
    """
    result = text

    # --- Time phrasing ---

    # "quarter past X" → "X:15" (handles "quarter past 10", "quarter past ten")
    def _quarter_past(m):
        num_str = m.group(1)
        h = _word_to_number(num_str)
        if h is not None:
            return f"{h}:15"
        return m.group(0)
    result = re.sub(r'quarter\s+past\s+(\w+)', _quarter_past, result, flags=re.IGNORECASE)

    # "half past X" → "X:30"
    def _half_past(m):
        num_str = m.group(1)
        h = _word_to_number(num_str)
        if h is not None:
            return f"{h}:30"
        return m.group(0)
    result = re.sub(r'half\s+past\s+(\w+)', _half_past, result, flags=re.IGNORECASE)

    # "quarter to X" → "(X-1):45"
    def _quarter_to(m):
        num_str = m.group(1)
        h = _word_to_number(num_str)
        if h is not None:
            return f"{h - 1}:45" if h > 0 else "23:45"
        return m.group(0)
    result = re.sub(r'quarter\s+to\s+(\w+)', _quarter_to, result, flags=re.IGNORECASE)

    # "half an hour" / "half hour" → "30 minutes"
    result = re.sub(r'half\s+(?:an?\s+)?hour', '30 minutes', result, flags=re.IGNORECASE)

    # "an hour" / "one hour" / "1 hour" → "60 minutes"
    result = re.sub(r'(?:an|one|1)\s+hour\b', '60 minutes', result, flags=re.IGNORECASE)

    # "X hours" → "X*60 minutes"
    def _hours_to_min(m):
        n = int(m.group(1))
        return f"{n * 60} minutes"
    result = re.sub(r'(\d+)\s+hours?\b', _hours_to_min, result, flags=re.IGNORECASE)

    # "in the morning" → "AM"
    result = re.sub(r'\bin\s+the\s+morning\b', 'AM', result, flags=re.IGNORECASE)

    # "in the afternoon" / "in the evening" → "PM"
    result = re.sub(r'\bin\s+the\s+(?:afternoon|evening)\b', 'PM', result, flags=re.IGNORECASE)

    # "at night" → "PM" only when followed by a digit (time context)
    result = re.sub(r'\bat\s+night\s+(?=\d)', 'PM ', result, flags=re.IGNORECASE)

    # "tonight" → do NOT normalize (too context-dependent, corrupts message bodies)
    # result = re.sub(r'\btonight\b', 'PM', result, flags=re.IGNORECASE)  # REMOVED

    # "tomorrow morning" → "AM" only when followed by a digit
    result = re.sub(r'\btomorrow\s+morning\s+(?=\d)', 'AM ', result, flags=re.IGNORECASE)

    # --- Verb aliases for send_message ---

    # "shoot/fire/ping/drop X a text/message (saying Y)"
    result = re.sub(
        r'\b(?:shoot|fire|ping|drop)\s+(\w+)\s+(?:a\s+)?(?:quick\s+)?(?:text|message|msg)',
        r'send message to \1 saying', result, flags=re.IGNORECASE
    )

    # "hit up X" → "send message to X"
    result = re.sub(r'\bhit\s+up\s+(\w+)', r'send message to \1', result, flags=re.IGNORECASE)

    # --- Weather phrasing ---

    # "outside in X" → "weather in X"
    result = re.sub(r'\boutside\s+in\s+', 'weather in ', result, flags=re.IGNORECASE)

    # "how's it in X" → "weather in X"
    result = re.sub(r"how'?s\s+it\s+in\s+", 'weather in ', result, flags=re.IGNORECASE)

    # "what's it like outside" → "weather"
    result = re.sub(r"what'?s\s+it\s+like\s+outside", 'weather', result, flags=re.IGNORECASE)

    # --- Timer alias ---

    # "countdown" → "timer"  (for keyword matching; keeps original for readability)
    # Not replaced in text, handled by keyword table

    # --- Contact alias ---

    # "phonebook" → "search contacts"
    result = re.sub(r'\bphonebook\b', 'search contacts', result, flags=re.IGNORECASE)

    return result


_WORD_NUMBERS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12,
}


def _word_to_number(s):
    """Convert word or digit string to int. Returns None if not recognized."""
    s_lower = s.strip().lower()
    if s_lower in _WORD_NUMBERS:
        return _WORD_NUMBERS[s_lower]
    try:
        return int(s_lower)
    except ValueError:
        return None


# ============ Rule-based argument extraction ============


def _extract_location(text):
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
    # "H:MM AM/PM"
    m = re.search(r'(\d{1,2}):(\d{2})\s*(AM|PM|am|pm|a\.m\.|p\.m\.)', text)
    if m:
        h, mi = int(m.group(1)), int(m.group(2))
        ampm = m.group(3).upper().replace('.', '')
        if ampm == 'PM' and h != 12:
            h += 12
        if ampm == 'AM' and h == 12:
            h = 0
        return h, mi

    # "H AM/PM"
    m = re.search(r'(\d{1,2})\s*(AM|PM|am|pm|a\.m\.|p\.m\.)', text)
    if m:
        h = int(m.group(1))
        ampm = m.group(2).upper().replace('.', '')
        if ampm == 'PM' and h != 12:
            h += 12
        if ampm == 'AM' and h == 12:
            h = 0
        return h, 0

    # "at H:MM" or "for H:MM"
    m = re.search(r'(?:at|for)\s+(\d{1,2})(?::(\d{2}))?\b', text)
    if m:
        h = int(m.group(1))
        mi = int(m.group(2)) if m.group(2) else 0
        return h, mi

    return None, None


def _extract_time_string(text):
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
    m = re.search(r'(\d+)\s*(?:minute|min)', text, re.IGNORECASE)
    if m:
        return int(m.group(1))
    m = re.search(r'(?:for|timer)\s+(\d+)', text, re.IGNORECASE)
    if m:
        return int(m.group(1))
    return None


def _extract_recipient_and_message(text):
    # "to <Name> saying <message>"
    m = re.search(r'(?:to|tell)\s+(\w+)\s+(?:saying|that|:)\s+(.+?)(?:\.|,\s+and\s+|,\s+|$)', text, re.IGNORECASE)
    if m:
        name = m.group(1).strip()
        if name.lower() not in ('him', 'her', 'them'):
            return name, m.group(2).strip().rstrip('.')

    # "<Name> a message saying <message>"
    m = re.search(r'(\w+)\s+a\s+message\s+saying\s+(.+?)(?:\.|,\s+and\s+|,\s+|$)', text, re.IGNORECASE)
    if m:
        name = m.group(1).strip()
        if name.lower() not in ('send', 'him', 'her', 'them', 'a', 'the'):
            return name, m.group(2).strip().rstrip('.')

    # "<verb> <Name> saying <message>"
    m = re.search(r'(?:text|message|msg)\s+(\w+)\s+(?:saying|that|:)\s+(.+?)(?:\.|,\s+and\s+|,\s+|$)', text, re.IGNORECASE)
    if m:
        return m.group(1).strip(), m.group(2).strip().rstrip('.')

    # "send <message> to <Name>"
    m = re.search(r'send\s+(.+?)\s+to\s+(\w+)', text, re.IGNORECASE)
    if m:
        return m.group(2).strip(), m.group(1).strip()

    # "send message to <Name> saying <msg>" (post-normalization form)
    m = re.search(r'send\s+message\s+to\s+(\w+)\s+saying\s+(.+?)(?:\.|,\s+and\s+|,\s+|$)', text, re.IGNORECASE)
    if m:
        return m.group(1).strip(), m.group(2).strip().rstrip('.')

    # "send message to <Name>" (no explicit message body — use remainder)
    m = re.search(r'send\s+message\s+to\s+(\w+)\s+(.+?)(?:\.|,\s+and\s+|,\s+|$)', text, re.IGNORECASE)
    if m:
        name = m.group(1).strip()
        msg = m.group(2).strip().rstrip('.')
        if name.lower() not in ('a', 'the', 'my', 'to'):
            return name, msg

    # "text <Name> <message>" (no "saying")
    m = re.search(r'(?:text|message)\s+(\w+)\s+(.+?)(?:\.|,\s+and\s+|,\s+|$)', text, re.IGNORECASE)
    if m:
        name = m.group(1).strip()
        msg = m.group(2).strip().rstrip('.')
        if name.lower() not in ('a', 'the', 'my', 'to', 'saying'):
            return name, msg

    # "tell <Name> <message>"
    m = re.search(r'tell\s+(\w+)\s+(.+?)(?:\.|,\s+and\s+|,\s+|$)', text, re.IGNORECASE)
    if m:
        return m.group(1).strip(), m.group(2).strip().rstrip('.')

    return None, None


def _extract_reminder_title_and_time(text):
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
    m = re.search(r'play\s+(.+?)(?:\.|,\s+and\s+|,\s+|$)', text, re.IGNORECASE)
    if m:
        song = m.group(1).strip().rstrip('.')
        song = re.sub(r'^(?:some|a|the|my)\s+', '', song, flags=re.IGNORECASE)
        return song
    m = re.search(r'listen\s+to\s+(.+?)(?:\.|,\s+and\s+|,\s+|$)', text, re.IGNORECASE)
    if m:
        return m.group(1).strip().rstrip('.')
    return None


def _extract_contact_query(text):
    m = re.search(r'(?:find|look\s*up|search\s+for|search\s+contacts?\s+for)\s+(\w+)', text, re.IGNORECASE)
    if m:
        name = m.group(1).strip()
        if name.lower() not in ('a', 'the', 'my', 'in', 'for'):
            return name
    return None


def _extract_args_for_tool(tool_name, user_text, cactus_args):
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


# ============ JSON / sanitize ============

def _repair_json_payload(raw_str):
    s = re.sub(r':\s*0(\d+)(?=\s*[,}\]])', r':\1', raw_str)
    s = re.sub(r',\s*([}\]])', r'\1', s)
    s = s.replace("'", '"')
    return s


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

def _is_multi_action(user_text):
    text_lower = user_text.lower()
    markers = (" and ", " then ", " also ", " plus ", ", and ")
    return any(m in text_lower for m in markers)


def _split_multi_action(user_text):
    normalized = re.sub(r',\s+and\s+', ' |SPLIT| ', user_text, flags=re.IGNORECASE)
    normalized = re.sub(r',\s+', ' |SPLIT| ', normalized)
    normalized = re.sub(r'\s+and\s+', ' |SPLIT| ', normalized, flags=re.IGNORECASE)
    parts = [p.strip() for p in normalized.split('|SPLIT|') if p.strip()]
    if len(parts) <= 1:
        return [user_text]
    return parts


def _extract_names_from_text(text):
    words = text.split()
    names = []
    for w in words:
        clean = w.strip('.,!?')
        if clean and clean[0].isupper() and clean.isalpha() and len(clean) > 1:
            if clean.lower() not in ('set', 'play', 'find', 'look', 'send', 'text', 'check',
                                      'get', 'what', 'how', 'the', 'and', 'remind', 'i', 'am', 'pm',
                                      'can', 'could', 'please', 'hey', 'ok', 'sure'):
                names.append(clean)
    return names


def _resolve_pronouns_in_subrequests(sub_requests, full_text):
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


# ============ Core inference ============

def _call_cactus_single(user_text, all_tools):
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
        confidence_threshold=0.0,
        tool_rag_top_k=3,
        stop_sequences=["<end_of_turn>"]
    )
    elapsed = (time.time() - start) * 1000

    try:
        raw = json.loads(raw_str)
    except json.JSONDecodeError:
        try:
            raw = json.loads(_repair_json_payload(raw_str))
        except json.JSONDecodeError:
            m = re.search(r'"name"\s*:\s*"([^"]+)"', raw_str)
            guessed_tool = m.group(1) if m else _select_tool_by_keywords(user_text, all_tools)
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
        if not isinstance(call, dict):
            continue
        name = call.get("name")
        args = call.get("arguments", {})
        if not isinstance(args, dict):
            args = {}

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

    # v3 NEW: normalize input before any processing
    user_text = _normalize_input(user_text)

    if _is_multi_action(user_text):
        sub_requests = _split_multi_action(user_text)
        sub_requests = _resolve_pronouns_in_subrequests(sub_requests, user_text)

        all_calls = []
        total_time = 0

        for sub_req in sub_requests:
            res = _call_cactus_single(sub_req, tools)
            all_calls.extend(res.get("function_calls", []))
            total_time += res.get("total_time_ms", 0)

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
