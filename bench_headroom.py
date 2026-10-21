#!/usr/bin/env python3
"""Benchmark: headroom tool output compression.

Simulates a multi-turn agent session with realistic large tool outputs,
measures context chars/tokens with and without compression.

Usage:
    .venv/bin/python bench_headroom.py

Run on both branches to compare:
    git checkout main      # baseline
    .venv/bin/python bench_headroom.py   # should show NO compression
    git checkout headroom-only
    .venv/bin/python bench_headroom.py   # should show compression ratios
"""

import json
import sys
import os

# Generate realistic tool outputs that bloat context
def generate_tool_outputs():
    """Generate realistic large outputs from various tools."""

    # 1. terminal output: ls -la on a large directory
    terminal_ls = "\n".join([
        f"drwxr-xr-x  2 xeio xeio  4096 Jun 29 10:{i:02d} {name}"
        for i, name in enumerate([f"module_{j}" for j in range(300)])
    ])

    # 2. read_file: large Python file
    read_file_py = json.dumps({
        "content": "\n".join([
            f"def function_{i}():\n    # Docstring for function {i}\n    x = compute_{i}(arg_a, arg_b)\n    return x + offset_{i}\n"
            for i in range(200)
        ]),
        "path": "/home/xeio/dev/project/large_module.py",
        "total_lines": 800
    }, indent=2)

    # 3. search_files: many matches
    search_files = json.dumps({
        "total_count": 500,
        "matches": [
            {"file": f"/project/src/module_{i}.py", "line": i*10, "content": f"def handler_{i}(): pass"}
            for i in range(500)
        ]
    }, indent=2)

    # 4. web_extract: large page
    web_extract = "\n".join([
        f"# Section {i}\n\nThis is paragraph {i} with some Lorem ipsum dolor sit amet content. "
        f"The model processes this information and generates output based on the context window.\n"
        f"Key metrics: accuracy={0.5+i*0.001:.4f}, loss={1.0-i*0.002:.4f}\n"
        for i in range(300)
    ])

    # 5. terminal output: pip list / large command output
    terminal_pip = "\n".join([
        f"{pkg:<30} {ver:<15} ({loc})"
        for i, (pkg, ver, loc) in enumerate([
            (f"package-{i}", f"{i}.0.{i}", "/home/xeio/.local/lib/python3.12/site-packages")
            for i in range(400)
        ])
    ])

    # 6. terminal output: stack trace with many frames
    traceback_output = "Traceback (most recent call last):\n"
    for i in range(100):
        traceback_output += f'  File "/app/module_{i}.py", line {i*10+5}, in function_{i}\n'
        traceback_output += f'    result = call_{i}(arg_a, arg_b, arg_c)\n'
    traceback_output += "\nValueError: Something went wrong deep in the stack\n"

    # 7. Jupyter notebook output (auto-extracted)
    notebook_output = "\n".join([
        f"## Cell {i}\n\n```python\ncell_{i}_result = run_computation({i})\n```\n\n"
        f"Output: array([{'  '.join(str(j) for j in range(20))}])\n"
        for i in range(150)
    ])

    return [
        ("terminal", terminal_ls),
        ("read_file", read_file_py),
        ("search_files", search_files),
        ("web_extract", web_extract),
        ("terminal", terminal_pip),
        ("terminal", traceback_output),
        ("read_file", notebook_output),
    ]


def estimate_tokens(chars: int) -> int:
    """Rough token estimate: ~4 chars per token for English/code."""
    return chars // 4


def run_benchmark():
    tool_outputs = generate_tool_outputs()

    total_original = 0
    total_compressed = 0
    results = []

    print("=" * 80)
    print("HEADROOM COMPRESSION BENCHMARK")
    print("=" * 80)
    print()

    # Try to import the compressor
    try:
        from agent.tool_output_compressor import compress_tool_result, cache_stats, clear_cache, _reset_state
        has_compressor = True
    except (ImportError, ModuleNotFoundError) as e:
        print(f"[WARN] Compressor not available: {e}")
        print("[INFO] Running on baseline branch (no compression)")
        has_compressor = False

    cfg = {
        "enabled": True,
        "min_chars": 500,      # lower threshold for demo
        "min_reduction_pct": 5, # lower threshold for demo
    } if has_compressor else {}

    for tool_name, output in tool_outputs:
        orig_len = len(output)
        total_original += orig_len

        if has_compressor:
            compressed = compress_tool_result(tool_name, output, config=cfg)
            final = compressed if compressed is not None else output
        else:
            final = output

        final_len = len(final)
        total_compressed += final_len

        reduction = ((orig_len - final_len) / orig_len * 100) if orig_len > 0 else 0
        status = f"{reduction:5.1f}%" if reduction > 0 else "  -- "

        results.append({
            "tool": tool_name,
            "original": orig_len,
            "compressed": final_len,
            "reduction": reduction,
            "status": status,
        })

    # Print per-tool breakdown
    print(f"{'Tool':<15} {'Original':>10} {'Result':>10} {'Saved':>8} {'Status'}")
    print("-" * 60)
    for r in results:
        print(f"{r['tool']:<15} {r['original']:>10,} {r['compressed']:>10,} {r['status']:>7} {r['status']}")

    print("-" * 60)
    total_reduction = ((total_original - total_compressed) / total_original * 100) if total_original > 0 else 0
    print(f"{'TOTAL':<15} {total_original:>10,} {total_compressed:>10,} {total_reduction:>6.1f}%")

    # Token estimates
    orig_tokens = estimate_tokens(total_original)
    comp_tokens = estimate_tokens(total_compressed)
    token_saved = orig_tokens - comp_tokens
    print()
    print("Estimated token impact:")
    print(f"  Without compression: {orig_tokens:,} tokens")
    print(f"  With compression:    {comp_tokens:,} tokens")
    print(f"  Tokens saved:        {token_saved:,} ({total_reduction:.1f}%)")
    print()

    # Context window context
    context_32k = (32000 - comp_tokens)
    context_128k = (128000 - comp_tokens)
    context_no_comp_32k = (32000 - orig_tokens)
    print("Remaining context window (approximate):")
    print(f"  32K model:  {context_no_comp_32k:>8,} tokens without headroom, {context_32k:>8,} tokens with headroom")
    print(f"  128K model: {context_128k:>8,} tokens with headroom")
    if context_no_comp_32k < 0:
        print("  >>> 32K model WOULD EXHAUST context without compression!")
    print()

    # Multi-turn simulation
    turns = 10
    print(f"Multi-turn simulation ({turns} turns, same tools each turn):")
    context_with = turns * total_compressed
    context_without = turns * total_original
    print(f"  {turns} turns without: {context_without:,} chars ({estimate_tokens(context_without):,} tokens)")
    print(f"  {turns} turns with:    {context_with:,} chars ({estimate_tokens(context_with):,} tokens)")
    print(f"  Gap after {turns} turns: {context_without - context_with:,} chars ({estimate_tokens(context_without - context_with):,} tokens)")
    print()

    # Cache stats
    if has_compressor:
        stats = cache_stats()
        print(f"Cache: {stats['cached_items']} items / {stats['max_cache_size']} max")
        clear_cache()

    print()
    print("=" * 80)
    if not has_compressor:
        print("RESULT: No compression available (baseline branch)")
    elif total_reduction > 15:
        print(f"RESULT: {total_reduction:.1f}% reduction — meaningful context savings")
    else:
        print(f"RESULT: {total_reduction:.1f}% reduction — minimal savings")
    print("=" * 80)


if __name__ == "__main__":
    # Ensure we can import from the project root
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    run_benchmark()
