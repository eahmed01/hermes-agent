# Handoff — hermes catch-up (2026-10-21)

Working dir: `~/dev/hermes/catchup-wt` (branch `catchup-2026-10-21`, base `nous/main`).
Kanban: `docs/kanban_2026-10-21-hermes-catchup.md`.

## What was done

All 23 local commits (from the old live repo `~/code/hermes-agent`, `origin/local-main`) were
3-way re-ported onto the 2026-10-21 upstream tip, feature by feature. See the kanban for the
per-feature list and the "deliberately dropped" table (5 features superseded by upstream).

## Verification evidence (all real runs, 2026-10-21)

- venv: `python3 -m pm.build_env --source . --out .venv --group dev --group test` → EXIT=0
- import smoke: run_agent, model_tools, toolsets, consultation_tool, headroom_retrieve,
  agent.display, agent.context_compressor, tui_gateway.tool_progress → OK
- Python (scripts/run_tests.sh):
  - batch 1 (8 files): 491 passed, 1 failed → the failure was a wrong assertion in the NEW
    sanitize test (expected `"tool"` for `"///"`, impl returns `"___"`); test fixed.
  - re-run sanitize (7 tests): 7 passed.
  - tests/tui_gateway/test_tui_gateway_server.py: 638 passed, 0 failed.
- ui-tui: `npm ci` (164 pkgs) → `npm run build:ink` → `tsc --noEmit` (typecheck) clean →
  i18n key manifest regenerated (`locales/_keys.tui.json`) → vitest + lint (final counts in
  /tmp/vitest2.log, /tmp/lint.log).

## Next steps (in order)

1. Confirm vitest + lint green (this handoff's pending evidence).
2. `git add` the changed files explicitly (selective staging) and commit on `catchup-2026-10-21`.
3. Promote: `mv ~/dev/hermes/0 ~/dev/hermes/0.back`; create fresh `~/dev/hermes/0` as a worktree
   (or clone checkout) of `catchup-2026-10-21`.
4. Reinstall live hermes from the new `0` (editable), verify `hermes --version` + that
   `consultation_ask`, `headroom_retrieve` tools and TUI Ctrl+R/Ctrl+T are live.
5. Leave `~/code/hermes-agent` untouched (per user).

## Key files

- `docs/kanban_2026-10-21-hermes-catchup.md` — status + drop rationale
- `tui_gateway/contracts/events.py` — `ToolCompletePayload.diff_error` (contract)
- `apps/shared/src/gateway-contract.generated.ts` / `.openrpc.json` — regenerated
- `agent/context_compressor.py` — 25K / 10% summary budget (deliberate deviation from upstream 10K)
- `ui-tui/src/app/useInputHandlers.ts` — section hotkeys
- `locales/en.yaml` + `locales/_keys.tui.json` — patch diff-stat + hotkey labels

## Blockers / risks

- None blocking. Watch item: the compressor ceiling is intentionally higher than upstream's
  thrash-fix (10K→25K). If compaction thrash reappears in live use, revisit `context_length*0.10`
  / `_SUMMARY_TOKENS_CEILING`.
