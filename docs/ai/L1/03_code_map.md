# 03 · Code Map

> Where things live. Two top-level modules: `web/` (Next.js client) and `server/` (FastAPI backend + LLM endpoint). Orchestration is in the root `package.json`.

## Root

| Path                  | Responsibility                                                                          |
| --------------------- | --------------------------------------------------------------------------------------- |
| `package.json`        | Bun workspace; `setup`, `dev`, `doctor*`, `verify*`, `clean` scripts.                  |
| `README.md`           | Setup, run modes, env, ngrok step, troubleshooting.                                     |
| `ARCHITECTURE.md`     | System shape, one-process/two-concerns design, API table.                               |
| `AGENTS.md`           | Coding-agent handbook + Git Conventions + How to Load.                                  |
| `Dockerfile`          | Single-process image (`:8000`): agent backend + LLM endpoint in one container.         |
| `.github/workflows/`  | `ci.yml` (backend pytest matrix + web verify), `docker.yml` (build + smoke), `nightly.yml`. |

## `server/` — FastAPI backend (:8000)

| Path                              | Responsibility                                                                              |
| --------------------------------- | ------------------------------------------------------------------------------------------- |
| `src/server.py`                   | FastAPI app, CORS, route handlers, error mapping, mounts `llm_app` at `/llm`, uvicorn entrypoint. |
| `src/agent.py`                    | `Agent` class: `AsyncAgora` client, `CustomLLM`/`DeepgramSTT`/`MiniMaxTTS` vendor chain, `start()`/`stop()`, `_sessions`. |
| `src/llm.py`                      | Provider-agnostic OpenAI-compatible mock LLM endpoint; `run_agent_turn()` + `log_message()` + `list_messages()` over SQLite. No `agora_agent` import. |
| `scripts/run_fake_server.py`      | Boots `server.app` with a `FakeAgent` for the local FastAPI smoke test.                    |
| `tests/test_tools.py`             | Unit tests for `run_agent_turn`, `log_message`, `list_messages`, and SQLite persistence.  |
| `tests/test_llm.py`               | Contract tests for the LLM endpoint in isolation (SSE format, non-streaming rejection).   |
| `tests/test_llm_mount.py`         | Asserts `/llm/*` is mounted in the server app and `llm.py` has no Agora import.          |
| `tests/test_agent_construction.py`| Builds the real `AgoraAgent`, fakes the SDK session, asserts shape.                      |
| `tests/conftest.py`               | `fake_env` fixture + `FakeAgent`; no cloud, no real creds.                                |
| `.env.example`                    | Env template (do not add `PORT`).                                                         |
| `requirements*.txt`               | Runtime + dev (pytest) deps.                                                              |

## `server/src/server.py` routes

- `GET /get_config` — token + channel/UID config.
- `POST /startAgent` — start the cascading-vendor agent session.
- `POST /stopAgent` — stop by `agent_id`.
- `/llm/*` — mounted sub-application (LLM endpoint, see `server/src/llm.py`).

## `server/src/llm.py` routes

- `POST /chat/completions` — OpenAI-compatible completions (Agora cloud calls this).
- `GET /health` — LLM endpoint health check.

## `web/` — Next.js client (:3000)

| Path                                      | Responsibility                                                    |
| ----------------------------------------- | ----------------------------------------------------------------- |
| `next.config.ts`                          | `/api/*` rewrites to `AGENT_BACKEND_URL`; strict mode; Turbopack root. |
| `src/services/api.ts`                     | Browser API client: `getConfig`, `startAgent`, `stopAgent`.       |
| `src/lib/conversation.ts`                 | Transcript normalization, timestamp/UID mapping, visualizer state.|
| `src/lib/agora.ts`                        | Agora RTC/RTM helpers.                                            |
| `src/components/LandingPage.tsx`          | Conversation entry: config fetch, agent start, RTM login, teardown.|
| `src/components/ConversationComponent.tsx`| RTC join, mic publish, transcript/metrics/state listeners.        |
| `scripts/verify-api-contracts.ts`         | Asserts rewrites + client paths + response envelope (no network). |
| `scripts/verify-local-proxy.ts`           | Stub backend; proxies `/api/*` through the rewrite map.           |
| `scripts/verify-local-fastapi.ts`         | Spawns real FastAPI with `FakeAgent`; proxies routes end-to-end.  |
| `scripts/verify-local-llm.ts`             | Spawns the LLM server; asserts SSE contract + non-streaming rejection. |
| `scripts/doctor.ts`                       | Web prerequisite check.                                           |

## Related Deep Dives

- None. For runtime flow see [02_architecture](02_architecture.md); for contracts see [06_interfaces](06_interfaces.md).
