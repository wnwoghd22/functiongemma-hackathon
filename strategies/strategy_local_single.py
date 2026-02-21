import json
import os
import re
import sys
import time
from typing import List, Dict, Any

sys.path.insert(0, "cactus/python/src")
from cactus import cactus_init, cactus_complete, cactus_destroy

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


def _generate_cactus_single(messages, tools, system_prompt):
    model = cactus_init(_FUNCTIONGEMMA_PATH)
    cactus_tools = [{"type": "function", "function": t} for t in tools]
    
    start = time.time()
    raw_str = cactus_complete(
        model,
        [{"role": "system", "content": system_prompt}] + messages,
        tools=cactus_tools,
        force_tools=True,
        max_tokens=512,
        temperature=0.0,
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
            return {"function_calls": [], "confidence": 0, "success": False, "total_time_ms": elapsed}

    return {
        "function_calls": _sanitize_function_calls(raw.get("function_calls", []), tools),
        "confidence": raw.get("confidence", 0),
        "success": raw.get("success", True),
        "total_time_ms": elapsed
    }


def generate_hybrid(messages, tools, confidence_threshold=0.99):
    prompt = "You are a strict function-calling router. Output only function calls, never conversational text."
    res = _generate_cactus_single(messages, tools, prompt)
    res["source"] = "on-device"
    return res
