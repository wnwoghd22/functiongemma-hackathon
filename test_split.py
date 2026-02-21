import re

def _split_multi_action(user_text):
    normalized = re.sub(r',\s+and\s+', ' |SPLIT| ', user_text, flags=re.IGNORECASE)
    normalized = re.sub(r',\s+', ' |SPLIT| ', normalized)
    normalized = re.sub(r'\s+and\s+', ' |SPLIT| ', normalized, flags=re.IGNORECASE)
    parts = [p.strip() for p in normalized.split('|SPLIT|') if p.strip()]
    if len(parts) <= 1:
        return [user_text]
    return parts

cases = [
    "Send a message to Bob saying hi and get the weather in London.",
    "Set an alarm for 7:30 AM and check the weather in New York.",
    "Set a 15 minute timer, play classical music, and remind me to stretch at 4:00 PM."
]

for c in cases:
    print(f"\nOriginal: {c}")
    print("Split:", _split_multi_action(c))
