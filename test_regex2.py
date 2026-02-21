import re
import json

text = '{"success":true,"error":null,"cloud_handoff":false,"response":"","function_calls":[{"name":"send_message","arguments":{"message":"good morning","recipient：<escape>Alice<escape>}":}}],"confidence":0.9971}'

s = re.sub(r'"([^"]+)：<escape>([^<]+)<escape>[^"]*":\}', r'"\1": "\2"}', text)
print("Regex:")
print(s)

try:
    j = json.loads(s)
    print("VALID JSON!")
except Exception as e:
    print("Error:", e)
