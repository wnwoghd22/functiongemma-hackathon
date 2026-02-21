
import sys
sys.path.insert(0, "cactus/python/src")
functiongemma_path = "cactus/weights/functiongemma-270m-it"

import json, os, time
from cactus import cactus_init, cactus_complete, cactus_destroy
from google import genai
from google.genai import types


def generate_cactus(messages, tools):
    """Run function calling on-device via FunctionGemma + Cactus."""
    model = cactus_init(functiongemma_path)

    cactus_tools = [{
        "type": "function",
        "function": t,
    } for t in tools]

    raw_str = cactus_complete(
        model,
        [{"role": "system", "content": "You are a helpful assistant that can use tools."}] + messages,
        tools=cactus_tools,
        force_tools=True,
        max_tokens=256,
        stop_sequences=["<|im_end|>", "<end_of_turn>"],
    )

    cactus_destroy(model)

    try:
        raw = json.loads(raw_str)
    except json.JSONDecodeError:
        return {
            "function_calls": [],
            "total_time_ms": 0,
            "confidence": 0,
        }

    return {
        "function_calls": raw.get("function_calls", []),
        "total_time_ms": raw.get("total_time_ms", 0),
        "confidence": raw.get("confidence", 0),
    }


def generate_cloud(messages, tools):
    """Run function calling via Gemini Cloud API."""
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

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

    gemini_response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=contents,
        config=types.GenerateContentConfig(tools=gemini_tools),
    )

    total_time_ms = (time.time() - start_time) * 1000

    function_calls = []
    for candidate in gemini_response.candidates:
        for part in candidate.content.parts:
            if part.function_call:
                function_calls.append({
                    "name": part.function_call.name,
                    "arguments": dict(part.function_call.args),
                })

    return {
        "function_calls": function_calls,
        "total_time_ms": total_time_ms,
    }


def generate_hybrid(messages, tools, confidence_threshold=0.99):
    """Hybrid routing with minimal, general-purpose quality gates."""
    local = generate_cactus(messages, tools)
    local_calls = local.get("function_calls") or []
    local_conf = local.get("confidence", 0)
    local_time_ms = local.get("total_time_ms", 0)

    # If cloud fallback was already observed to fail, stay on-device for the rest of this run.
    if getattr(generate_hybrid, "_disable_cloud_fallback", False):
        local["source"] = "on-device"
        return local

    tool_by_name = {t.get("name"): t for t in tools if t.get("name")}
    valid_tool_names = set(tool_by_name.keys())

    def _is_multi_action_request():
        user_text = " ".join(
            str(m.get("content", ""))
            for m in messages
            if m.get("role") == "user"
        ).lower()
        markers = (" and ", " then ", " also ", " plus ", ", and ", " 그리고 ", " 및 ")
        return any(marker in user_text for marker in markers) or user_text.count(",") >= 2

    def _needs_cloud_fallback():
        # Rule 1: Output Integrity Gate
        if local_conf == 0 and local_time_ms == 0 and not local_calls:
            return True, "parse_fail_sentinel", True

        for call in local_calls:
            if not isinstance(call, dict):
                return True, "invalid_call_shape", True
            if not isinstance(call.get("name"), str):
                return True, "invalid_call_name", True
            if not isinstance(call.get("arguments"), dict):
                return True, "invalid_call_arguments", True
            if valid_tool_names and call["name"] not in valid_tool_names:
                return True, "unknown_tool_name", True

        # Rule 2: Empty-Call Safety Gate
        if tools and not local_calls:
            return True, "empty_function_calls", True

        # Rule 3: Argument Sanity Gate
        for call in local_calls:
            schema = tool_by_name.get(call["name"], {}).get("parameters", {})
            required = schema.get("required", [])
            properties = schema.get("properties", {})
            args = call.get("arguments", {})

            for req_key in required:
                value = args.get(req_key)
                if req_key not in args:
                    return True, "missing_required_argument", True
                if value is None:
                    return True, "null_required_argument", True
                if isinstance(value, str) and not value.strip():
                    return True, "empty_required_string", True

            for key, prop in properties.items():
                if key not in args:
                    continue
                value = args[key]
                prop_type = str(prop.get("type", "")).lower()

                if prop_type == "integer":
                    if isinstance(value, bool):
                        return True, "invalid_integer_type", True
                    if isinstance(value, float):
                        if not value.is_integer():
                            return True, "invalid_integer_value", True
                        value = int(value)
                    if not isinstance(value, int):
                        return True, "invalid_integer_type", True

                    if key == "hour" and not (0 <= value <= 23):
                        return True, "hour_out_of_range", True
                    if key == "minute" and not (0 <= value <= 59):
                        return True, "minute_out_of_range", True
                    if key == "minutes" and value < 0:
                        return True, "negative_minutes", True

        # Rule 4: Multi-Action Risk Gate
        if _is_multi_action_request() and len(local_calls) < 2:
            return True, "multi_action_under_called", True

        # Existing confidence route
        if local_conf < confidence_threshold:
            return True, "low_confidence", False

        return False, "on_device_ok", False

    def _generate_cloud_with_model(model_name):
        client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
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
        gemini_response = client.models.generate_content(
            model=model_name,
            contents=contents,
            config=types.GenerateContentConfig(tools=gemini_tools),
        )
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

    needs_cloud, fallback_reason, critical = _needs_cloud_fallback()
    if not needs_cloud:
        local["source"] = "on-device"
        return local

    # Rule 5: Cost-Aware Cloud Routing (lite first, escalate only for critical cases).
    fallback_model = os.environ.get("GEMINI_MODEL_FALLBACK", "gemini-2.5-flash-lite")
    escalation_model = os.environ.get("GEMINI_MODEL_ESCALATE", "gemini-2.5-flash")
    models_to_try = [fallback_model]
    if critical and escalation_model not in models_to_try:
        models_to_try.append(escalation_model)

    last_error = None
    for model_name in models_to_try:
        try:
            cloud = _generate_cloud_with_model(model_name)
            cloud["source"] = "cloud (fallback)"
            cloud["local_confidence"] = local_conf
            cloud["total_time_ms"] += local_time_ms
            cloud["fallback_reason"] = fallback_reason
            cloud["cloud_model"] = model_name
            return cloud
        except Exception as e:
            last_error = e

    # Keep benchmark running even if cloud model/config/network is unavailable.
    generate_hybrid._disable_cloud_fallback = True
    local["source"] = "on-device"
    local["cloud_error"] = str(last_error) if last_error else "unknown_cloud_error"
    local["fallback_reason"] = fallback_reason
    return local


def print_result(label, result):
    """Pretty-print a generation result."""
    print(f"\n=== {label} ===\n")
    if "source" in result:
        print(f"Source: {result['source']}")
    if "confidence" in result:
        print(f"Confidence: {result['confidence']:.4f}")
    if "local_confidence" in result:
        print(f"Local confidence (below threshold): {result['local_confidence']:.4f}")
    print(f"Total time: {result['total_time_ms']:.2f}ms")
    for call in result["function_calls"]:
        print(f"Function: {call['name']}")
        print(f"Arguments: {json.dumps(call['arguments'], indent=2)}")


############## Example usage ##############

if __name__ == "__main__":
    tools = [{
        "name": "get_weather",
        "description": "Get current weather for a location",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "City name",
                }
            },
            "required": ["location"],
        },
    }]

    messages = [
        {"role": "user", "content": "What is the weather in San Francisco?"}
    ]

    on_device = generate_cactus(messages, tools)
    print_result("FunctionGemma (On-Device Cactus)", on_device)

    cloud = generate_cloud(messages, tools)
    print_result("Gemini (Cloud)", cloud)

    hybrid = generate_hybrid(messages, tools)
    print_result("Hybrid (On-Device + Cloud Fallback)", hybrid)
