---
title: Tool Output Compression
sidebar_position: 5
description: "Compress large tool outputs before they enter conversation context — save tokens, stay within limits"
---

# Tool Output Compression (Headroom)

Hermes Agent can compress large tool outputs **before** they enter your
conversation context. This cuts token usage without triggering full
conversation compression, keeping the agent fast and within context limits.

Compression is **lossy by design** — the middle sections of repetitive
output are replaced with summaries. The original is cached in memory for
retrieval, but once evicted from the cache, it is permanently lost.

## Quick Start

```bash
# Enable compression
hermes config set context.headroom.enabled true

# Disable
hermes config set context.headroom.enabled false
```

Compression is **off by default**. Toggle it on when you notice large tool
outputs (terminal sessions, file reads, search results) consuming too many
tokens.

## How It Works

When enabled, every tool output passes through a compression filter **after**
the tool runs but **before** the result enters the conversation context. The
agent loop sees the compressed version.

Two compression strategies run in sequence:

1. **SmartCrusher** (requires `headroom-ai` package) — specializes in JSON
   and structured data. Removes redundant whitespace, collapses repeated
   array entries, and preserves representative samples.

2. **Heuristic text compressor** (built-in, no extra package) — handles
   code, logs, and plain text. Keeps the first and last lines, detects
   repetitive patterns (numbered output, uniform prefixes), and preserves
   error-like lines (Traceback, Error, Exception) with context.

If neither strategy achieves at least 20% reduction (configurable), the
original output passes through unchanged.

Any error — import failure, config error, compression exception — returns
the original output unmodified. **The system is fail-open.**

## Retrieving Full Originals

When compression triggers, the tool result includes a cache marker:

```
[COMPRESSED by headroom (smartcrusher): 75% saved, 15,234→3,809 chars]
...
[Full output cached: hash=abc123def456]
```

The agent can retrieve the full original with:

```python
headroom_retrieve(hash="abc123def456")
```

**Important:** The cache is **process-bound** (cleared on Hermes restart)
with a max of 1000 items (LRU eviction). Once evicted, the full original
is **permanently lost** — compression is lossy. Retrieve early for
critical content before the cache fills up.

## Configuration

All settings live under `context.headroom` in `config.yaml`:

```yaml
context:
  headroom:
    enabled: false                    # Toggle compression on/off
    exclude_tools: []                 # Never compress these tools (e.g. ["memory_search"])
    min_chars: 2000                   # Skip outputs shorter than this
    min_reduction_pct: 20             # Skip if compression saves less than this %
    max_output_chars: 8000            # Hard cap on compressed output size
    keep_head_lines: 10               # Head lines preserved (heuristic strategy)
    keep_tail_lines: 5                # Tail lines preserved (heuristic strategy)
    cache_max: 1000                   # In-memory cache slots for originals (LRU)
```

Or set individual keys via CLI:

```bash
hermes config set context.headroom.min_chars 3000
hermes config set context.headroom.cache_max 2000
```

## Optional Package: SmartCrusher

For best results on JSON/structured data (search results, terminal output,
API responses), install the optional `headroom-ai` package:

```bash
pip install 'hermes-agent[headroom]'
```

Without it, only the heuristic text compressor runs — still useful for
large code files and logs, but misses the structured data optimizations.

### Tuning SmartCrusher

SmartCrusher's aggressiveness is configurable under
`context.headroom.crush_smartcrusher`. The shipped defaults are
conservative (they retain more rows than the library defaults) — raise
`max_items_after_crush` to keep more, or raise `min_tokens_to_crush` to
skip smaller outputs:

```yaml
context:
  headroom:
    crush_smartcrusher:
      max_items_after_crush: 50    # rows kept after crushing (lib default 15)
      min_tokens_to_crush: 1000    # skip outputs smaller than this (lib 200)
      min_items_to_analyze: 20     # avoid crushing short arrays (lib 5)
      first_fraction: 0.35         # leading rows retained (lib 0.30)
      last_fraction: 0.25          # trailing rows retained (lib 0.15)
      variance_threshold: 1.5      # outlier-row preservation (lib 2.0)
      uniqueness_threshold: 0.05   # lib default 0.10
      similarity_threshold: 0.90   # lib default 0.80
      preserve_change_points: true # keep points where values jump
      dedup_identical_items: true  # collapse exact duplicates
```

## Common Setups

**Default (just turn it on):**
```yaml
context:
  headroom:
    enabled: true
```

**Aggressive compression for long-running sessions:**
```yaml
context:
  headroom:
    enabled: true
    min_chars: 1000
    min_reduction_pct: 10
    cache_max: 2000
```

**Skip compression for specific tools:**
```yaml
context:
  headroom:
    enabled: true
    exclude_tools: ["memory_search", "session_search"]
```

## Tradeoffs

| | Full context compression | Tool output compression |
|---|---|---|
| **When it fires** | When conversation exceeds threshold | On every large tool output |
| **Cost** | Separate LLM call | Zero API cost (client-side) |
| **What it compresses** | Entire conversation history | Individual tool results |
| **Reversibility** | Summarized turns are lost | Originals cached in memory (limited) |
| **Token savings** | ~80% on compressed portion | ~75% on individual outputs |

Use both together: tool output compression keeps individual results small,
conversation compression handles the overall context growth.

## Troubleshooting

**Compression is not working:**
- Check `hermes config show` for `context.headroom.enabled`
- Verify outputs exceed `min_chars` (default 2000)
- Check that `headroom-ai` is installed for SmartCrusher: `pip show headroom-ai`

**Agent can't retrieve full output:**
- The cache may have evicted the original (max 1000 items, LRU)
- Increase `cache_max` for long-running sessions
- Retrieve critical content early in the conversation

**SmartCrusher errors:**
- Recompression falls through to heuristic — no data loss
- Run `pip install 'hermes-agent[headroom]'` for SmartCrusher support

## For Contributors

The compression hook lives inline in `model_tools.py:handle_function_call()` —
after tool dispatch, before `post_tool_call` hooks. This placement ensures
zero overhead when disabled (fast-path returns before any import).

Key files:

| File | Purpose |
|---|---|
| `agent/tool_output_compressor.py` | Core compression engine |
| `model_tools.py` (lines ~1175) | Inline hook that calls the compressor |
| `tools/headroom_retrieve.py` | Agent-facing retrieval tool |
| `toolsets.py` | `headroom` toolset definition |
| `hermes_cli/config.py` | `context.headroom` defaults |
| `tests/agent/test_tool_output_compressor.py` | Compressor tests |
| `tests/tools/test_headroom_retrieve.py` | Tool + integration tests |

The design is **fail-open**: any error (import failure, config error,
compression exception) returns `None` and the original output passes
through unchanged. Built-in features that need zero-overhead disabled
paths hook inline — see approval, edit-approval, and observability context
in the same function for the pattern.
