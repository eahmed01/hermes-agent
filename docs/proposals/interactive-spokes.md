# Interactive Spokes: Persistent Agent-to-Agent Conversations

## Status

Draft — not implemented.

## Problem

The hub conversation (user ↔ agent) is a shared context window. Every tool call,
every traceback, every diff bleeds into it. As tasks grow, the hub fills with
implementation noise — the agent loses sight of the high-level plan because its
own context is clogged with low-level details.

Current mechanisms for offloading work:

| Mechanism       | Hub stays clean? | Multi-turn? | Hub steers mid-task? |
|-----------------|------------------|-------------|----------------------|
| `delegate_task` | Yes (summary only) | No — one-shot | No — fire and wait |
| tmux spawn      | No (terminal noise) | Yes | Yes, but fragile |
| Kanban          | Yes | Yes | Dispatcher, not agent |
| `cronjob`       | Yes | No | No — scheduled |

Nothing gives a hub agent a **persistent, steerable worker whose internals
stay encapsulated**.

### Concrete Pain Points

1. **One-shot delegation wastes context.** Parent delegates → child returns
   summary → parent tries to act on it but hits an error → parent re-delegates
   with "try this instead" — each round loses everything the child learned.
   A dialogue would let the child say "I already tried X, here's what happened"
   and iterate from there.

2. **Implementation detail leaks into hub.** When the agent uses tmux to
   interact with a spawned Hermes, terminal capture includes spinner output,
   tool progress lines, and partial renders — all of which enters the hub's
   context window as noise.

3. **No mid-task steering.** The hub cannot ask "what's blocking you?" or
   "switch to approach B" without either killing the child or waiting for it
   to finish its current trajectory.

## Proposal: Spoke Protocol

A spoke is a persistent child agent that the hub can converse with across
multiple turns. The spoke maintains its own conversation history. The hub
receives only structured summaries — never raw tool output.

### Hub Perspective (What the User Sees)

```
You: Decompose the auth service into 3 spokes.

Agent: Spawned 3 spokes:
  spoke_1 (auth-impl): Implementing OAuth2 auth service
  spoke_2 (auth-tests): Writing test suite
  spoke_3 (auth-docs): Creating API documentation

You: Check on auth-impl.

Agent: spoke_1 progress: Writing middleware.py (turn 4/20)
  Blocked: dependency conflict between jose and pyjwt.
  Question: which library should I use?

You: Use pyjwt, drop jose.

Agent: Directed spoke_1: "Use pyjwt, drop jose."

You: /spokes

Agent: Active spokes:
  spoke_1 (auth-impl): working, turn 6, 14k in / 28k out
  spoke_2 (auth-tests): idle, awaiting impl completion
  spoke_3 (auth-docs): working, turn 3, 8k in / 12k out
```

The hub conversation reads like a project manager's log — strategic, compact,
no tracebacks.

### Tool API

Five hub-facing tools:

```python
# --- Lifecycle ---

spawn_spoke(
    name: str,                        # human-readable label
    goal: str,                        # system/goal prompt for the spoke
    model: str = None,                # optional model override
    toolsets: list[str] = None,       # restricted tool access
    max_turns: int = 20,              # hard cap on spoke turns
    budget_limit: float = None,       # optional per-spoke token budget
) -> str                              # returns spoke_id

kill_spoke(spoke_id: str) -> dict     # terminate immediately
reap_spoke(spoke_id: str) -> dict     # graceful finish, return summary

# --- Interaction ---

spoke_direct(
    spoke_id: str,
    directive: str,                   # new instruction from hub
) -> dict                             # {"status": "acknowledged", "turn": N}

spoke_ask(
    spoke_id: str,
    question: str,                    # query the spoke
) -> dict                             # {"answer": "summarized response", "turn": N}

spoke_status(spoke_id: str) -> dict   # progress, turns, budget, current_task

# --- Discovery ---

list_spokes() -> list[dict]           # all active spokes
```

### Information Flow

```
Hub → Spoke:  Full directives, file contents, context
               (hub sends exactly what the spoke needs)

Spoke → Hub:  Structured summaries only
               (spoke's tool output, errors, diffs never enter hub context)
```

The summarization layer is the key design element. When a spoke completes a
turn, its output is compressed into a compact status update before being
returned to the hub as a tool result. This keeps hub context windows lean.

Two summarization modes:

1. **`spoke_direct`** — spoke responds with acknowledgment + what it will do
   next. Compact by nature.

2. **`spoke_ask`** — spoke answers the question, optionally including relevant
   context (e.g., "I tried X, got error Y, recommend Z"). The spoke is
   instructed to summarize rather than dump raw output.

3. **`reap_spoke`** — spoke produces a final summary: files created/modified,
   tests passing, known issues. Similar to `delegate_task` summary but
   enriched with multi-turn context.

### Spoke Internals

Each spoke is a child `AIAgent` instance with:

- **Independent conversation history** — the spoke sees its own full dialogue
  with the hub. New directives append to existing history.
- **Restricted toolset** — spokes cannot delegate, clarify, or schedule
  cron jobs. They get the tools needed for their work (file, terminal, etc.).
- **Budget tracking** — per-spoke in/out token counts, visible to hub.
- **Turn limit** — hard cap prevents runaway loops. Configurable default
  (20 turns).
- **Clean termination** — if the hub session ends, all spokes are killed.
  No orphans.

### Implementation Approach

Build alongside the existing `delegate_tool.py` (~2800 lines) which already
handles:

- Spawning child `AIAgent` instances via `multiprocessing.get_context("spawn")`
- Process isolation
- Tool set configuration
- Output capture and summarization
- Budget tracking

New code:

1. **`_SpokeRegistry`** — in-process registry of active spokes (map from
   `spoke_id` to child process + session state). Tracks lifecycle, budget,
   turn count.

2. **`_SpokeChannel`** — message transport between hub and spoke. Injects
   user messages into the child's context, collects responses, runs
   summarization. Reuses the existing child process pattern from
   `delegate_tool.py`.

3. **Summarization hook** — when a spoke responds, its output is run through
   a lightweight compression pass before entering hub context. Can use the
   existing auxiliary summarization infrastructure or a simple length-based
   truncation with LLM summarization for longer outputs.

4. **Five tool handlers** — registered via `registry.register()`, each
   delegating to the registry + channel.

Estimated new code: 400-600 lines plus tool schema definitions.

### Configuration

```yaml
delegation:
  spokes:
    enabled: true                      # default: true
    max_concurrent: 5                  # hard cap on active spokes
    default_max_turns: 20             # per-spoke turn limit
    default_budget_limit: 0.0         # 0 = no limit
    summarize_output: true             # always summarize spoke → hub
    summary_model: "auto"             # auxiliary model for summarization
```

### What This Is Not

- **Not a replacement for `delegate_task`** — one-shot delegation is still
  the right choice for bounded subtasks that don't need mid-task steering.
  Spokes are for longer, exploratory work where iteration matters.

- **Not a replacement for Kanban** — Kanban is durable (survives process
  restarts) and dispatcher-driven. Spokes are ephemeral (live within the hub
  session) and agent-driven.

- **Not user-facing** — the user doesn't interact with spokes directly. The
  hub agent is the sole operator. The user sees the benefit as a cleaner,
  more capable hub conversation.

### Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| Token cost — each round-trip is a full API call | Per-spoke budget caps, turn limits, visible in `/spokes` |
| Latency — 5-turn dialogue = 10 API calls | Acceptable trade-off for quality; hub can batch directives |
| Spoke goes off-rails | Turn limits, budget caps, `kill_spoke` as emergency stop |
| Hub doesn't understand spoke state | Structured status responses, `list_spokes` overview |
| Memory leak — spokes accumulate | Hub session end kills all spokes; explicit `reap` / `kill` |

### Future Extensions

- **Cross-spoke communication** — spokes reference each other's outputs
  (e.g., spoke_2 waits for spoke_1's code before writing tests).
- **Persistent spokes** — survive hub session restart via Kanban-like
  durability.
- **Spoke templates** — predefined configurations (coder, reviewer, tester,
  researcher) with curated toolsets and system prompts.
- **Hub-to-hub** — nested spokes (spoke spawns its own spoke). Probably
  a bad idea; the whole point is keeping the hub lean.

### Decision Log

- 2026-06-21 — Initial proposal. Gap identified: no multi-turn steerable
  subagent with encapsulated internals.
