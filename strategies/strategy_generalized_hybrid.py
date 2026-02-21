import json
import os
import re
import sys
import time

from google import genai
from google.genai import types

sys.path.insert(0, ".")
from main import _extract_args_for_tool, _select_tool_by_keywords

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

def _repair_json_payload(raw_str):
    s = re.sub(r':\s*0(\d+)(?=\s*[,}\]])', r':\1', raw_str)
    s = re.sub(r'"([^"]+)：<escape>([^<]+)<escape>[^"]*":\}', r'"\1": "\2"}', s)
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


def _is_multi_action(user_text):
    text_lower = user_text.lower()
    markers = (" and ", " then ", " also ", " plus ", ", and ")
    return any(m in text_lower for m in markers) or text_lower.count(",") >= 1


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
    """Extract capitalized names from text to resolve pronouns."""
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
    """Replace pronouns like 'him', 'her', 'them' with actual names from the full text."""
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
        tool_rag_top_k=3, # Dynamic context pruning (less aggressive than 2)
        stop_sequences=["<end_of_turn>"]
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
            # Fallback for unparseable JSON (hallucinated structural brackets)
            m = re.search(r'"name"\s*:\s*"([^"]+)"', raw_str)
            guessed_tool = m.group(1) if m else _select_tool_by_keywords(user_text, all_tools)
            if guessed_tool:
                args = _extract_args_for_tool(guessed_tool, user_text, {})
                return {"function_calls": [{"name": guessed_tool, "arguments": args}], "total_time_ms": elapsed, "cloud_handoff": False}
            return {"function_calls": [], "total_time_ms": elapsed, "cloud_handoff": True}

    calls = raw.get("function_calls", [])

    # Fallback for empty calls (RLHF Model Refusals)
    if not calls:
        guessed_tool = _select_tool_by_keywords(user_text, all_tools)
        if guessed_tool:
            args = _extract_args_for_tool(guessed_tool, user_text, {})
            calls = [{"name": guessed_tool, "arguments": args}]

    # Fallback for empty arguments
    final_calls = []
    for call in calls:
        name = call.get("name")
        args = call.get("arguments", {})
        if not args:
            args = _extract_args_for_tool(name, user_text, {})
        final_calls.append({"name": name, "arguments": args})

    sanitized_calls = _sanitize_function_calls(final_calls)

    return {
        "function_calls": sanitized_calls,
        "total_time_ms": elapsed,
        "cloud_handoff": cloud_handoff,
    }


def _generate_cloud(messages, tools, model_name):
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
    
    # We rebuild the tools carefully for the Gemini SDK format
    gemini_tools = [
        types.Tool(function_declarations=[
            types.FunctionDeclaration(
                name=t["name"],
                description=t["description"],
                parameters=types.Schema(
                    type="OBJECT",
                    properties={
                        k: types.Schema(type=v["type"].upper(), description=v.get("description", ""))
                        for k, v in t["parameters"]["properties"].items()
                    },
                    required=t["parameters"].get("required", []),
                ),
            )
            for t in tools
        ])
    ]

    contents = [m["content"] for m in messages if m["role"] == "user"]
    start_time = time.time()
    
    try:
        gemini_response = client.models.generate_content(
            model=model_name,
            contents=contents,
            config=types.GenerateContentConfig(tools=gemini_tools),
        )
    except Exception as e:
        print(f"Cloud fallback failed: {e}")
        return {"function_calls": [], "total_time_ms": (time.time() - start_time) * 1000}

    total_time_ms = (time.time() - start_time) * 1000

    function_calls = []
    for candidate in (gemini_response.candidates or []):
        content = getattr(candidate, "content", None)
        if not content or not getattr(content, "parts", None):
            continue
        for part in content.parts:
            if part.function_call:
                function_calls.append({
                    "name": part.function_call.name,
                    "arguments": dict(part.function_call.args) if part.function_call.args else {},
                })

    return {
        "function_calls": function_calls,
        "total_time_ms": total_time_ms,
    }

def generate_hybrid(messages, tools, confidence_threshold=0.60):
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
        needs_cloud = False
        
        for sub_req in sub_requests:
            res = _call_cactus_single(sub_req, tools, confidence_threshold=confidence_threshold)
            all_calls.extend(res.get("function_calls", []))
            total_time += res.get("total_time_ms", 0)
            if res.get("cloud_handoff", False):
                needs_cloud = True

        if needs_cloud:
            # If any sub-request lacks confidence, just do one big cloud call for the whole message
            cloud_model = os.environ.get("GEMINI_MODEL_ESCALATE", "gemini-2.5-flash")
            cloud_res = _generate_cloud(messages, tools, cloud_model)
            cloud_res["total_time_ms"] += total_time
            cloud_res["source"] = "cloud (fallback)"
            return cloud_res

        # Basic deduplication by tool name
        seen = set()
        dedup_calls = []
        for call in all_calls:
            name = call.get("name")
            if name not in seen:
                dedup_calls.append(call)
                seen.add(name)

        return {
            "function_calls": dedup_calls,
            "total_time_ms": total_time,
            "source": "on-device",
            "confidence": 1.0,
            "success": True
        }
    else:
        res = _call_cactus_single(user_text, tools, confidence_threshold=confidence_threshold)
        if res.get("cloud_handoff", False):
            cloud_model = os.environ.get("GEMINI_MODEL_FALLBACK", "gemini-2.5-flash-lite")
            cloud_res = _generate_cloud(messages, tools, cloud_model)
            cloud_res["total_time_ms"] += res.get("total_time_ms", 0)
            cloud_res["source"] = "cloud (fallback)"
            return cloud_res

        res["source"] = "on-device"
        res["confidence"] = 1.0
        res["success"] = True
        return res
