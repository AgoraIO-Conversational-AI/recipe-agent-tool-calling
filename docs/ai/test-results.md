# Progressive Disclosure — Test Results

> Test run for `recipe-agent-tool-calling` progressive disclosure docs.
> Date: 2026-06-25 · Standard: AgoraIO-Community/ai-devkit progressive-disclosure.

## Step 1 — Structural checks

| Check                                              | Result |
| -------------------------------------------------- | ------ |
| `L0_repo_card.md` ≤ 50 lines                       | Pass (36) |
| All 8 L1 files present                             | Pass |
| Each L1 has purpose blockquote + Related Deep Dives| Pass (8/8) |
| L1 line counts in 80–200 target                    | **Partially below target** (46–94) — see note |
| L2 `_index.md` present                             | Pass |
| Each L2 opens with "When to Read This" callout     | Pass (2/2) |
| Relative links resolve (`docs/ai/` + AGENTS.md)    | Pass (35/35, 0 broken) |
| AGENTS.md has How to Load / Git Conventions / Doc Commands | Pass |

**Note on L1 line counts:** Files 02–04 and 07–08 run 46–69 lines, below the 80–200 soft target. The standard favors tables over prose and warns against bloat; files are table-dense and information-complete. Accepted deviation; revisit if a section needs more depth.

## Step 2/3 — Question runs

Questions span the five standard categories. Each answer was checked against the
repo source before being marked Pass. "Level" is the lowest disclosure level
that fully answers the question.

### Setup & Build

| # | Question | Expected answer | Source of truth | Level | Status |
|---|----------|-----------------|-----------------|-------|--------|
| 1 | How do I install and run it locally? | `bun run setup` then expose backend via ngrok, set `CUSTOM_LLM_URL`, then `bun run dev` (backend :8000 + web :3000). | `L1/01_setup.md` ↔ `README.md`, `package.json` | L1 | Pass |
| 2 | Which env vars are required? | `AGORA_APP_ID`, `AGORA_APP_CERTIFICATE`, `CUSTOM_LLM_URL`, `CUSTOM_LLM_API_KEY`. | `L1/01_setup.md`, `L1/06_interfaces.md` ↔ `agent.py`, `.env.example` | L1 | Pass |
| 3 | Is this zero-key? | Yes — the mock LLM endpoint requires no external LLM API key; the full pipeline runs out of the box. | `L1/01_setup.md` ↔ `README.md`, `llm.py` | L1 | Pass |

### Test & Run

| # | Question | Expected answer | Source of truth | Level | Status |
|---|----------|-----------------|-----------------|-------|--------|
| 4 | How do I run backend tests without cloud creds? | `cd server && pytest tests -v`; `conftest.py` fakes env + SDK session; 14 tests across tool logic, LLM contract, mount, and agent construction. | `L1/04_conventions.md`, `L1/01_setup.md` ↔ `tests/conftest.py` | L1 | Pass (ran: 14 passed) |
| 5 | What's the narrowest gate for a web-only change? | `bun run verify:web`. | `L1/05_workflows.md` ↔ `package.json` | L1 | Pass |
| 6 | What does `verify:local:llm` do? | Spawns the LLM server and asserts SSE contract + non-streaming rejection (no cloud, no creds). | `L1/03_code_map.md`, `L1/05_workflows.md` ↔ `web/scripts/verify-local-llm.ts` | L1 | Pass |

### Conventions

| # | Question | Expected answer | Source of truth | Level | Status |
|---|----------|-----------------|-----------------|-------|--------|
| 7 | What response shape do backend routes use? | `{ code, msg, data }`; `data` only when there's a payload. | `L1/04_conventions.md`, `L1/06_interfaces.md` ↔ `server.py` | L1 | Pass |
| 8 | Why must `llm.py` have no Agora import? | It is the provider-agnostic part a developer replaces; `test_llm_mount.py` enforces this via AST check. | `L1/04_conventions.md` ↔ `tests/test_llm_mount.py` | L1 | Pass |
| 9 | What are the commit/branch conventions? | Conventional commits `type: description`; branches `type/short-description`; no AI tool names. | `AGENTS.md` Git Conventions | L1 | Pass |

### Development

| # | Question | Expected answer | Source of truth | Level | Status |
|---|----------|-----------------|-----------------|-------|--------|
| 10 | How do I add a new tool? | Add the tool function in `server/src/llm.py`, add trigger keywords or model-based routing in `run_agent_turn()`, add a test in `test_tools.py`, verify with `pytest tests -v`. | `L1/05_workflows.md` ↔ `llm.py`, `tests/test_tools.py` | L1 | Pass |
| 11 | Why can't `CUSTOM_LLM_URL` be localhost? | Agora cloud (not the browser) calls the LLM endpoint. A localhost URL lets the agent "start" while LLM calls silently fail cloud-side. | `L1/07_gotchas.md` ↔ `agent.py` | L1 | Pass |
| 12 | How do I replace the mock LLM with a real model? | Edit `run_agent_turn()` in `server/src/llm.py`; keep the OpenAI SSE streaming contract and `llm.py` Agora-free. | `L1/05_workflows.md` ↔ `llm.py`, `tests/test_llm.py` | L1 | Pass |

### Deep Dive

| # | Question | Expected answer | Source of truth | Level | Status |
|---|----------|-----------------|-----------------|-------|--------|
| 13 | How does the tool loop work and why does Agora never see a tool_call? | `run_agent_turn()` executes tools synchronously; only the final plain-text reply enters the streaming generator. The SSE stream contains no `tool_call` keys. | `L2/tool_calling_flow.md` ↔ `llm.py` | L2 | Pass |
| 14 | What SSE format must the LLM endpoint speak? | Role chunk → content chunks (word-by-word) → `finish_reason: stop` → `data: [DONE]`. Must use `stream: true`; non-streaming returns 400. | `L2/tool_calling_flow.md` ↔ `llm.py`, `tests/test_llm.py` | L2 | Pass (test covers it) |
| 15 | How does stop survive a backend restart? | `_sessions` is in-memory; missing session falls back to `self.client.stop_agent(agent_id)` (stateless cloud path). | `L2/session_lifecycle.md` ↔ `agent.py` | L2 | Pass |

## Step 4 — Analysis

- All 15 questions answered at the expected disclosure level (12 at L1, 3 at L2).
  No "correct but needed L2 unnecessarily" or "wrong/missing L2" cases.
- No missing-coverage findings; no broken references.
- One soft deviation: several L1 files below the 80–200 line target (accepted; concise/table-dense).

## Step 5 — Summary

| Category       | Questions | Pass | Notes |
| -------------- | :-------: | :--: | ----- |
| Setup & Build  | 3 | 3 | — |
| Test & Run     | 3 | 3 | backend tests executed: 14 passed |
| Conventions    | 3 | 3 | — |
| Development    | 3 | 3 | — |
| Deep Dive      | 3 | 3 | resolved at L2 as designed |
| **Total**      | **15** | **15** | — |

## Step 6 — Fixes / Retest

No failing questions; no fixes required. Evidence executed during this run:

- `pytest tests -v` (throwaway venv `/tmp/v_tool_calling`) → `14 passed, 1 warning`.
- Relative link check → `35 checked, 0 broken`.
