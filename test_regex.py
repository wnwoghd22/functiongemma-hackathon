import re

text = '{"success":true,"error":null,"cloud_handoff":false,"response":"","function_calls":[{"name":"send_message","arguments":{"message":"good morning","recipient：<escape>Alice<escape>}":}}],"confidence":0.9971}'
print("Original:")
print(text)

s = re.sub(r'"([^"]+)：<escape>([^<]+)<escape>[^"]*":\}', r'"\1":"\2"', text)
print("Regex 1:", s)
