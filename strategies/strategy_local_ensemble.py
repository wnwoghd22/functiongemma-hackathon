import json
import os
import re
import sys
import time
from typing import List, Dict, Any

sys.path.insert(0, "cactus/python/src")
from cactus import cactus_init, cactus_complete, cactus_destroy, cactus_reset

_FUNCTIONGEMMA_PATH = "cactus/weights/functiongemma-270m-it"


def _repair_json_payload(raw_str):
    s = re.sub(r':\s*0(\d+)(?=\s*[,}\]])', r':\1', raw_str)
    s = re.sub(r'"([^"]+)：<escape>([^<]+)<escape>[^"]*":\}', r'"\1": "\2"}', s)
    return s


def _sanitize_string_value(value):
    return value.strip()


def _sanitize_function_calls(function_calls, tools):
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
            sanitized_args[new_key] = new_value
        sanitized_calls.append({"name": name, "arguments": sanitized_args})
    return sanitized_calls


def _is_multi_action_request(messages):
    user_text = " ".join(
        str(m.get("content", ""))
        for m in messages
        if m.get("role") == "user"
    ).lower()
    markers = (" and ", " then ", " also ", " plus ", ", and ", " 그리고 ", " 및 ")
    return any(marker in user_text for marker in markers) or user_text.count(",") >= 2


def _shallow_semantic_check(local_calls, messages):
    user_text = " ".join(
        str(m.get("content", ""))
        for m in messages
        if m.get("role") == "user"
    ).lower()
    for call in local_calls:
        args = call.get("arguments", {})
        for k, v in args.items():
            if isinstance(v, int):
                if v <= 0:
                    continue
                v_str = str(v)
                v_12_str = str(v - 12) if v > 12 else None
                if v_str not in user_text and (not v_12_str or v_12_str not in user_text):
                    if v == 12 and "noon" in user_text:
                        continue
                    return False
    return True


def _should_retry_local(local, messages, tools):
    local_calls = local.get("function_calls") or []
    local_conf = local.get("confidence", 0)
    local_time_ms = local.get("total_time_ms", 0)
    success = local.get("success", True)
    
    tool_by_name = {t.get("name"): t for t in tools if t.get("name")}
    valid_tool_names = set(tool_by_name.keys())

    if not success:
        return True

    if local_conf == 0 and local_time_ms == 0 and not local_calls:
        return True

    for call in local_calls:
        if not isinstance(call, dict):
            return True
        if not isinstance(call.get("name"), str):
            return True
        if not isinstance(call.get("arguments"), dict):
            return True
        if valid_tool_names and call["name"] not in valid_tool_names:
            return True

    if tools and not local_calls:
        return True

    for call in local_calls:
        schema = tool_by_name.get(call["name"], {}).get("parameters", {})
        required = schema.get("required", [])
        args = call.get("arguments", {})
        for req_key in required:
            if req_key not in args:
                return True
            value = args.get(req_key)
            if value is None or (isinstance(value, str) and not value.strip()):
                return True

    for call in local_calls:
        schema = tool_by_name.get(call["name"], {}).get("parameters", {})
        properties = schema.get("properties", {})
        args = call.get("arguments", {})
        for key, prop in properties.items():
            if key not in args:
                continue
            value = args[key]
            prop_type = str(prop.get("type", "")).lower()
            if prop_type == "integer" and isinstance(value, (int, float)) and not isinstance(value, bool):
                v = int(value) if isinstance(value, float) and value.is_integer() else value
                if isinstance(v, int):
                    if key == "hour" and not (0 <= v <= 23):
                        return True
                    if key == "minute" and not (0 <= v <= 59):
                        return True
                    if key in ("minutes", "seconds", "duration") and v < 0:
                        return True

    expected_multi = _is_multi_action_request(messages)
    if expected_multi and len(local_calls) < 2:
        return True

    if not _shallow_semantic_check(local_calls, messages):
        return True

    return False


def _generate_cactus_single(messages, tools, system_prompt, temp):
    model = cactus_init(_FUNCTIONGEMMA_PATH)
    cactus_tools = [{"type": "function", "function": t} for t in tools]
    
    start = time.time()
    raw_str = cactus_complete(
        model,
        [{"role": "system", "content": system_prompt}] + messages,
        tools=cactus_tools,
        force_tools=True,
        max_tokens=512,
        temperature=temp,
        confidence_threshold=0.0,
        tool_rag_top_k=0,
        stop_sequences=["<end_of_turn>"],
    )
    elapsed = (time.time() - start) * 1000

    cactus_destroy(model)

    try:
        raw = json.loads(raw_str)
    except json.JSONDecodeError:
        try:
            raw = json.loads(_repair_json_payload(raw_str))
        except json.JSONDecodeError:
            print(f"JSONDECODE ERROR: {raw_str}")
            return {"function_calls": [], "confidence": 0, "success": False, "total_time_ms": elapsed}

    return {
        "function_calls": _sanitize_function_calls(raw.get("function_calls", []), tools),
        "confidence": raw.get("confidence", 0),
        "success": raw.get("success", True),
        "total_time_ms": elapsed
    }


def generate_hybrid(messages, tools, confidence_threshold=0.99):
    # Pure local ensemble. Disable cloud entirely.
    total_time = 0
    best_result = None
    
    # Strategy 1: Strict Prompt + low temp (best for simple cases)
    prompt1 = "You are a strict function-calling router. Output only function calls, never conversational text."
    res1 = _generate_cactus_single(messages, tools, prompt1, temp=0.0)
    total_time += res1["total_time_ms"]
    
    if not _should_retry_local(res1, messages, tools):
        res1["total_time_ms"] = total_time
        res1["source"] = "on-device"
        return res1
        
    best_result = res1

    # Strategy 2: Helpful assistant + higher temp (sometimes helps with multi-action escapes)
    prompt2 = "You are a helpful assistant that can use tools. You must use tools to answer."
    res2 = _generate_cactus_single(messages, tools, prompt2, temp=0.3)
    total_time += res2["total_time_ms"]
    
    if not _should_retry_local(res2, messages, tools):
        res2["total_time_ms"] = total_time
        res2["source"] = "on-device (retry 1)"
        return res2
        
    if len(res2["function_calls"]) > len(best_result["function_calls"]):
        best_result = res2

    # Strategy 3: Highly assertive prompt + temp 0.5 (Hail Mary for hard multi-actions)
    prompt3 = "Return ONLY a JSON array of function calls. Do NOT wrap in markdown. Do NOT say absolutely anything else."
    res3 = _generate_cactus_single(messages, tools, prompt3, temp=0.5)
    total_time += res3["total_time_ms"]
    
    if not _should_retry_local(res3, messages, tools):
        res3["total_time_ms"] = total_time
        res3["source"] = "on-device (retry 2)"
        return res3
        
    if len(res3["function_calls"]) > len(best_result["function_calls"]):
        best_result = res3

    best_result["total_time_ms"] = total_time
    best_result["source"] = "on-device (failed validation)"
    return best_result
