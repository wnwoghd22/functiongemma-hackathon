import sys, json
sys.path.insert(0, "cactus/python/src")

from cactus import cactus_init, cactus_complete, cactus_destroy
from benchmark import BENCHMARKS

_FUNCTIONGEMMA_PATH = "cactus/weights/functiongemma-270m-it"
model = cactus_init(_FUNCTIONGEMMA_PATH)

PROMPT = """You are a function calling AI. Output ONLY a valid JSON array of function calls based on the provided tools. Do NOT output conversational text.
Example format:
User request: "Do action X"
[{"name": "example_tool", "arguments": {"param1": "value1"}}]"""

print("Testing WITH previous cases...")
for case in BENCHMARKS:
    if case["name"] in ["weather_sf", "alarm_10am", "weather_london"]:
        print(f"\n--- {case['name']} ---")
        cactus_tools = [{"type": "function", "function": t} for t in case["tools"]]
        
        raw = cactus_complete(
            model,
            [{"role": "system", "content": PROMPT}] + case["messages"],
            tools=cactus_tools,
            force_tools=True,
            max_tokens=512,
            temperature=0.0,
            confidence_threshold=0.0,
            tool_rag_top_k=2,
            stop_sequences=["<end_of_turn>"]
        )
        try:
            parsed = json.loads(raw)
            print("Calls:", parsed.get("function_calls"))
        except Exception as e:
            print("Raw failed:", raw)

cactus_destroy(model)

print("\n\nTesting ISOLATED...")
model = cactus_init(_FUNCTIONGEMMA_PATH)
for case in BENCHMARKS:
    if case["name"] in ["weather_london"]:
        print(f"\n--- {case['name']} ---")
        cactus_tools = [{"type": "function", "function": t} for t in case["tools"]]
        
        raw = cactus_complete(
            model,
            [{"role": "system", "content": PROMPT}] + case["messages"],
            tools=cactus_tools,
            force_tools=True,
            max_tokens=512,
            temperature=0.0,
            confidence_threshold=0.0,
            tool_rag_top_k=2,
            stop_sequences=["<end_of_turn>"]
        )
        try:
            parsed = json.loads(raw)
            print("Calls:", parsed.get("function_calls"))
        except Exception as e:
            print("Raw failed:", raw)
cactus_destroy(model)
