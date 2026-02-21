import json

def compute_total_score(results):
    difficulty_weights = {"easy": 0.20, "medium": 0.30, "hard": 0.50}
    time_baseline_ms = 500

    total_score = 0
    for difficulty, weight in difficulty_weights.items():
        group = [r for r in results if r["difficulty"] == difficulty]
        if not group: continue

        avg_f1 = sum(r["f1"] for r in group) / len(group)
        avg_time = sum(r["total_time_ms"] for r in group) / len(group)
        on_device_ratio = sum(1 for r in group if r["source"] == "on-device") / len(group)

        if avg_time <= time_baseline_ms:
            time_score = 1.0
        else:
            time_score = max(0, 1 - (avg_time - time_baseline_ms) / 1000.0)

        level_score = (0.50 * avg_f1) + (0.25 * time_score) + (0.25 * on_device_ratio)
        total_score += weight * level_score

    return total_score * 100

def get_dummy(diff, f1, time, source):
    return {"difficulty": diff, "f1": f1, "total_time_ms": time, "source": source}

# Scenario 1: ALL On-Device, F1 is 0.244, Time is ~400ms
local_results = [
    get_dummy("easy", 0.40, 400, "on-device"), 
    get_dummy("medium", 0.10, 400, "on-device"), 
    get_dummy("hard", 0.00, 400, "on-device")
]
score_local = compute_total_score(local_results)
print(f"Pure Local Score: {score_local:.2f}%")

# Scenario 2: ALL Cloud, F1 is 0.90, Time is ~1200ms
cloud_results = [
    get_dummy("easy", 0.95, 1200, "cloud"), 
    get_dummy("medium", 0.90, 1200, "cloud"), 
    get_dummy("hard", 0.85, 1200, "cloud")
]
score_cloud = compute_total_score(cloud_results)
print(f"Pure Cloud Score: {score_cloud:.2f}%")
