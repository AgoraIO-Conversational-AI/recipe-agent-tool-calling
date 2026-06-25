# Agent Development Guide

For coding agents working in `recipe-agent-tool-calling`. This repository is the
**tool-calling** recipe in the Agora Conversational AI recipes family.

## How to Load

This repository uses progressive disclosure documentation. Docs live under
`docs/ai/` in three levels.

1. Read [docs/ai/L0_repo_card.md](docs/ai/L0_repo_card.md) to identify the repo.
2. This repo declares `Recipe Role: base`; read [docs/ai/RECIPE.md](docs/ai/RECIPE.md) before changing reusable recipe contracts.
3. Load ALL 8 files in [docs/ai/L1/](docs/ai/L1/). They are small — load all upfront.
4. Follow L2 deep-dive links only when L1 isn't detailed enough. The index is at [docs/ai/L1/L2/_index.md](docs/ai/L1/L2/_index.md).

The sections below remain the canonical contributor handbook for hands-on work;
the `docs/ai/` tree is the structured summary used by AI agents.

## System shape

- **`server/`** — Python FastAPI agent backend (:8000). Owns Agora token
  generation and agent session lifecycle. Uses the `CustomLLM` vendor to point the
  agent's LLM stage at the tool-calling LLM endpoint. SDK: `agora-agents>=2.3.0`
  (`import agora_agent`).
- **`server/src/llm.py`** — provider-agnostic FastAPI tool-calling LLM endpoint,
  mounted into the API server at `/llm` (so Agora cloud calls
  `<public>/llm/chat/completions`). OpenAI-compatible `POST /chat/completions`
  mock that internally runs a tool loop over a SQLite message log:
  `run_agent_turn()` detects user intent and executes `log_message()` (persist a
  note) or `list_messages()` (read notes back), then streams only the spoken reply.
  No `agora-agents` dependency. This is the component a developer replaces.
- **`web/`** — Next.js 16 / React 19 / TypeScript frontend (:3000), resynced from
  the base quickstart.
- Auth: Token007 from `AGORA_APP_ID` + `AGORA_APP_CERTIFICATE`.

## Routing / ownership

- UI and RTC/RTM lifecycle live in `web/`.
- Browser-facing `/api/*` paths are Next rewrites (`web/next.config.ts`) to the
  agent backend; do not add `web/app/api/**/route.ts` for agent/token logic.
- Token generation and agent lifecycle live in `server/src/`.
- The OpenAI `/chat/completions` contract and internal tool loop live in
  `server/src/llm.py`.

## Supported modes

- **Local:** `bun run dev` starts `server` (:8000, serving `/llm`) and `web`
  (:3000). The web app calls `/api/*`; Next rewrites to
  `AGENT_BACKEND_URL=http://localhost:8000`. The backend must be exposed publicly
  (`ngrok http 8000`) so Agora cloud can reach `/llm/chat/completions`.
- **Deploy:** deploy `web` (Next) + `server` (a single publicly reachable FastAPI
  process that also serves `/llm`, so Agora cloud can reach
  `/llm/chat/completions`). Set `AGENT_BACKEND_URL` in the web deployment.

## Patterns

- Keep the web client calling `/api/*`; hide backend placement behind Next rewrites.
- Keep token generation and the App Certificate in `server/`.
- Keep `server/src/llm.py` free of `agora-agents` — it is provider-agnostic.
- `CUSTOM_LLM_URL` is required and must be public; there is no localhost default.
- Both `CUSTOM_LLM_URL` and `CUSTOM_LLM_API_KEY` are required by the `CustomLLM`
  vendor (the SDK rejects one without the other).
- The tool loop (`run_agent_turn` + `log_message` + `list_messages`) and its
  SQLite store belong in `server/src/llm.py`; do not move tool execution into a
  separate service.

## Anti-patterns

- Do not reintroduce Next Route Handlers for agent/token logic.
- Do not add `agora-agents` to `server/src/llm.py`.
- Do not default `CUSTOM_LLM_URL` to localhost.
- Do not put `PORT` in `server/.env.example` (it would clobber the random port
  that `verify:local:fastapi` injects via `load_dotenv(override=True)`).
- Do not skip the progressive disclosure docs — read [docs/ai/](docs/ai/L0_repo_card.md) before making changes.

## Commands

```bash
bun run setup
bun run dev
bun run doctor
bun run doctor:local
bun run verify         # web-only, no creds
bun run verify:local   # full local gate
```

Narrower checks: `bun run verify:backend`, `bun run verify:local:fastapi`,
`bun run verify:local:llm`, `bun run verify:web:proxy`.

## Done criteria

1. Run the narrowest relevant verification command.
2. Web-affecting changes: `bun run verify:web` passes.
3. Backend-affecting changes: `bun run verify:local` (or the narrower
   `verify:local:fastapi` / `verify:local:llm` / `verify:backend`) passes.
4. If you change required env vars or setup steps, update the root README, the
   relevant module README, and `server/.env.example` together.

## Git Conventions

### Commit messages — conventional commits

- **Format:** `type: description` or `type(scope): description`
- **Types:** `feat:` (new feature), `fix:` (bug fix), `chore:` (maintenance, version bumps), `test:` (test additions/changes), `docs:` (documentation)
- **Scoped variant:** `feat(scope):`, `fix(scope):` — e.g. `fix(server): validate custom llm url`
- **Lowercase after prefix** — `feat: add feature`, not `feat: Add feature`
- **Present tense** — "add feature", not "added feature"

### Branch names

- **Format:** `type/short-description` — lowercase, hyphen-separated
- **Types match commit types:** `feat/`, `fix/`, `chore/`, `test/`, `docs/`
- **Examples:** `feat/tool-calling-expansion`, `fix/custom-llm-url-validation`, `docs/progressive-disclosure`

### General rules

- **Repo-local `AGENTS.md` is the authoritative source for repo conventions.**
- **No AI tool names** — never mention claude, cursor, copilot, cody, aider, gemini, codex, chatgpt, or gpt-3/4 in commit messages or PR descriptions.
- **No Co-Authored-By trailers** — omit AI attribution lines.
- **No `--no-verify`** — let git hooks run normally.
- **No git config changes** — do not modify `user.name` or `user.email`.

## Doc Commands

| Command       | When to use                                                                  |
| ------------- | ---------------------------------------------------------------------------- |
| generate docs | No `docs/ai/` directory exists yet                                           |
| update docs   | Code changed since the `Last Reviewed` date in L0                            |
| test docs     | Verify docs give agents the right context (writes `docs/ai/test-results.md`) |
| fix docs      | Close findings from a docs review or test run                                |

See the [progressive disclosure standard](https://github.com/AgoraIO-Community/ai-devkit/blob/main/docs/standard/progressive-disclosure-standard.md) and [workflows](https://github.com/AgoraIO-Community/ai-devkit/blob/main/docs/workflows/progressive-disclosure-docs.md) for the full specification.
