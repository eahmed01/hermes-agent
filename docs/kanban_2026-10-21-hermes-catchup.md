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
- [x] c1 Verify: venv build, import smoke, targeted pytest (batch 491+1 fixed, sanitize 7/7,
      tui_gateway server 638/638), ui-tui (typecheck clean, vitest 1860/1860 across 236 files,
      lint 0 errors, i18n keys regenerated)
- [x] c2 Smoke: TUI boots from branch venv; hotkey overlay shows "Ctrl+R toggle reasoning
      visibility" + "Ctrl+T toggle tool call visibility"; consultation+headroom registered in
      toolsets; version v0.22.4+14 local be458508
- [x] d1 Promote: `~/dev/hermes/0` (old Jul-23 clone) → `0.back`; `0` is now the worktree of
      `catchup/20261021` @ be45850806 (`.venv` + `node_modules` carried over via
      `git worktree move`)
- [x] d2 Reinstall live hermes from the new `0`; verify version + tools; report
      (done via `1/` — the catchup-wt worktree — see 2026-10-27 note below)

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

## 2026-10-27 — rebased onto upstream tip e5ea5fd9cc

- `git rebase --onto nous/main 8685712f8f`: 2 commits replayed onto the 2026-10-27 upstream tip.
  One conflict: the compressor summary-success path — upstream extracted
  `_record_summary_success()` (a superset of the inline field writes); resolution kept the
  helper plus our "summary generated" log line. 25K/10% budget intact and still the only
  summary-budget clamp (`_compute_summary_budget`).
- scripts/check fixes folded in: consultation_tool.py budget read utf-8 → utf-8-sig
  (footguns); handoff doc /tmp literals reworded (no-tmp).
- Verified after rebase: 1638 passed / 0 failed (entire compression cluster, tui_gateway
  server 638, all 6 local feature test files). Net diff vs upstream tip unchanged:
  42 files, +3349/−28.
- d2 (live install) was in fact done via `1/` (the catchup-wt worktree): live install dir is
  `~/dev/hermes/1` reporting the local tip. Note: `0/.git` and `1/.git` both point at the
  same worktree admin dir (worktrees/catchup-wt) — they share branch ref + index.
- Known follow-up: 19 unwaived health findings on our own lines (BLE001 catch-alls in
  tool_output_compressor / consultation_tool / headroom_retrieve / display / model_tools /
  cli_agent_setup_mixin, S110 at display.py:1293, CC 22 on consultation_ask) — predate the
  rebase; the 10-21 work never ran scripts/check. Separately, scripts/check blob-size +
  health fail on ANY head in this repo because the baseline is the merge-base with the fork's
  stale main (ca988df8d0, 2026-07-23): it flags upstream's own recent files, not ours.
