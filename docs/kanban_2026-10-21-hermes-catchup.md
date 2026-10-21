# 2026-10-21 hermes catch-up — local 23 commits onto upstream tip

Branch: `catchup-2026-10-21` in `~/dev/hermes/hermes-agent.eahmed01`, worktree `~/dev/hermes/catchup-wt`.
Base: `nous/main` (upstream tip, 2026-10-21). Source of local work: `origin/local-main` (23 commits on
upstream@2026-07-08, previously the live editable install at `~/code/hermes-agent`).

## Status

- [x] a1 Scaffold (worktree + branch from nous/main)
- [x] a2 Per-feature patch extraction (docs/artifacts/2026-10-21-catchup/local-diffs/)
- [x] b1 Clean additions: consultation tool, headroom (tool_output_compressor + tool + bench + docs)
- [x] b2 toolsets.py / config wiring / model_tools.py
- [x] b3 ui-tui: Ctrl+R/Ctrl+T section hotkeys, hotkey help rows (i18n), edit-diff-preview error surfacing
- [x] b4 Agent layer: Qwen3.6+ preserve_thinking replay (6 files, grafted on upstream reasoning-route
      arch), anthropic tool-name sanitize, patch diff-stats line (+locales), compressor summary budget
      (25K ceiling / 10% ratio + log), vLLM "at least N" output-cap routing
- [x] b5 terminal sudo hardening (bytearray+TTL, moved to tools/terminal_tool_sudo.py),
      session-export system prompt section (+redaction), skin `user_text` input color
- [x] c1 Verify: venv build, import smoke, targeted pytest, ui-tui vitest
- [ ] c2 Smoke: TUI boots, Ctrl+R/Ctrl+T, timestamps (upstream), consultation tool, patch diff stats
- [ ] d1 Promote: `~/dev/hermes/0` → `0.back`; fresh `0` from this branch
- [ ] d2 Reinstall live hermes from new `0`; verify version + tools; report

## Deliberately DROPPED (superseded by upstream since 2026-07-08)

| Local feature | Upstream replacement |
|---|---|
| Message timestamps (strftime `timestamp_format`, 4977a47d8c) | #41531 `/timestamps`, fixed [HH:MM], `createdAt`, all 7 history surfaces via `session_history._history_to_messages`; compress response normalized |
| Model catalogs (GPT-6/GPT-5.6 curated list + sync_models.py markers) | `hermes_cli/models.py` rebuilt around `_openai_catalog` etc., already includes gpt-5.6-*/gpt-6-*/astra |
| exa pin `==2.10.2` → `>=2.10.2` | would force `uv lock` regeneration (lockfile `--check` in `pm install`); dropped to keep CI parity — re-pin in live 0 if wanted |
| cli.py edit-diff-preview red warning | classic CLI diff-preview block no longer exists upstream; TUI surfaces the failure via `tool.complete.diff_error` instead |
| MCP WIP (camelCase/snake_case result fields, dirty in ~/code) | `tools/mcp_tool_common.py::mcp_field(obj, snake, camel)` already used for `is_error`/`structured_content` |
| Local `test_context_compressor` absolute-value tests | upstream tests the budget with relative assertions; 25K/10% kept, verified by suite |

## Notes / judgment calls

- `context_compressor._SUMMARY_TOKENS_CEILING`: upstream had lowered to 10K in 76381e2a8e
  ("stop compaction thrash"). Local user intent (27ba73785c, "reduce lobotomization") kept: 25K +
  10% ratio. Verified against both compressor test suites.
- `diff_error` (edit-diff preview failure) required a contract change: `ToolCompletePayload.diff_error`
  in `tui_gateway/contracts/events.py` + regenerated `apps/shared` contract. Field renamed from local
  `_diff_error` to clean `diff_error`.
- `_cute_patch` renderer uses i18n keys added to `locales/en.yaml` (display.cute.patch_*).
