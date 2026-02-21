#!/usr/bin/env python3
import argparse
import importlib
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from benchmark import BENCHMARKS, compute_f1, compute_total_score


def run_strategy_benchmark(strategy_module, benchmarks=None):
    if benchmarks is None:
        benchmarks = BENCHMARKS

    mod = importlib.import_module(strategy_module)
    if not hasattr(mod, "generate_hybrid"):
        raise AttributeError(f"{strategy_module} has no generate_hybrid")
    generate_hybrid = mod.generate_hybrid

    total = len(benchmarks)
    results = []
    for i, case in enumerate(benchmarks, 1):
        print(f"[{i}/{total}] Running: {case['name']} ({case['difficulty']})...", end=" ", flush=True)
        result = generate_hybrid(case["messages"], case["tools"])
        f1 = compute_f1(result["function_calls"], case["expected_calls"])
        source = result.get("source", "unknown")
        print(f"F1={f1:.2f} | {result['total_time_ms']:.0f}ms | {source}")
        results.append({
            "name": case["name"],
            "difficulty": case["difficulty"],
            "total_time_ms": result["total_time_ms"],
            "f1": f1,
            "source": source,
            "predicted": result["function_calls"],
            "expected": case["expected_calls"],
        })

    print("\n=== Benchmark Results ===\n")
    print(f"  {'#':>2} | {'Difficulty':<10} | {'Name':<28} | {'Time (ms)':>10} | {'F1':>5} | Source")
    print(f"  {'--':>2}-+-{'-'*10}-+-{'-'*28}-+-{'-'*10}-+-{'-'*5}-+-{'-'*20}")
    for i, r in enumerate(results, 1):
        print(f"  {i:>2} | {r['difficulty']:<10} | {r['name']:<28} | {r['total_time_ms']:>10.2f} | {r['f1']:>5.2f} | {r['source']}")

    print("\n--- Summary ---")
    for difficulty in ["easy", "medium", "hard"]:
        group = [r for r in results if r["difficulty"] == difficulty]
        if not group:
            continue
        avg_f1 = sum(r["f1"] for r in group) / len(group)
        avg_time = sum(r["total_time_ms"] for r in group) / len(group)
        on_device = sum(1 for r in group if r["source"] == "on-device")
        cloud = len(group) - on_device
        print(
            f"  {difficulty:<8} avg F1={avg_f1:.2f}  avg time={avg_time:.2f}ms  "
            f"on-device={on_device}/{len(group)} cloud={cloud}/{len(group)}"
        )

    avg_f1 = sum(r["f1"] for r in results) / len(results)
    avg_time = sum(r["total_time_ms"] for r in results) / len(results)
    total_time = sum(r["total_time_ms"] for r in results)
    on_device_total = sum(1 for r in results if r["source"] == "on-device")
    cloud_total = len(results) - on_device_total
    print(f"  {'overall':<8} avg F1={avg_f1:.2f}  avg time={avg_time:.2f}ms  total time={total_time:.2f}ms")
    print(
        f"           on-device={on_device_total}/{len(results)} ({100*on_device_total/len(results):.0f}%)  "
        f"cloud={cloud_total}/{len(results)} ({100*cloud_total/len(results):.0f}%)"
    )

    score = compute_total_score(results)
    print(f"\n{'='*50}")
    print(f"  TOTAL SCORE: {score:.1f}%")
    print(f"{'='*50}")

    return score


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run benchmark with a selectable strategy module")
    parser.add_argument(
        "--strategy",
        default="main",
        help="Python module path containing generate_hybrid (e.g. main, strategies.strategy_balanced)",
    )
    args = parser.parse_args()
    run_strategy_benchmark(args.strategy)
