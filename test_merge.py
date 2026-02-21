import re
import sys

def parse_tool_name(raw_str):
    m = re.search(r'"name"\s*:\s*"([^"]+)"', raw_str)
    return m.group(1) if m else None

print(parse_tool_name('{"function_calls":[{"name":"play_music","arguments":{"song"":"Bohemian Rhapsody" by Queen}}]}'))
print(parse_tool_name('{"function_calls":[{"name":"set_alarm","arguments":{}}]}'))
