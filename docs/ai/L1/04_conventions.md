# 04 · Conventions

> Coding patterns shared across `server/` and `web/`. Follow these to keep local and deployed modes aligned.

## Boundary ownership

- Browser code calls only `/api/*`. Backend placement is hidden behind Next rewrites (`web/next.config.ts`).
- **Never** add `web/app/api/**/route.ts` for agent/token logic — `verify-api-contracts.ts` fails the build if a `route.ts` appears under `app/api`.
- Token generation and the App Certificate stay in `server/`.
- The LLM endpoint (`server/src/llm.py`) must stay free of `agora_agent` imports — `test_llm_mount.py` asserts this via AST inspection.

## Backend (Python / FastAPI)

- Async throughout: route handlers are `async def`; the agent uses `AsyncAgora` and `create_async_session`.
- Request bodies are Pydantic models (`StartAgentRequest`, `StopAgentRequest`). Field names are **camelCase** (`channelName`, `rtcUid`, `userUid`) to match the browser client.
- Error mapping is centralized: `_to_http_error()` maps `ValueError → 400`, `RuntimeError → 500`, else 500. `_log_route_error()` logs with safe context + traceback. Raise plain `ValueError`/`RuntimeError`; let the route convert.
- Logging via `logging.getLogger("uvicorn.error")`.
- Env read with `os.getenv`; `.env.local` then `.env` loaded with `override=True` in `server.py`.
- `Agent.__init__` raises `ValueError` immediately if `AGORA_APP_ID`, `AGORA_APP_CERTIFICATE`, `CUSTOM_LLM_URL`, or `CUSTOM_LLM_API_KEY` are missing. The server sets `agent = None` if init fails and returns 500 on all routes.

## Response envelope

All backend JSON responses use:

```json
{ "code": 0, "msg": "success", "data": { } }
```

`data` is present only when the route returns a payload. The browser client treats `code !== 0` (or missing `data`) as an error.

## Tool loop ownership

- The tool calls (`log_message`, `list_messages`) execute entirely inside `server/src/llm.py`. Keep them there.
- `run_agent_turn()` streams only the final spoken reply — Agora cloud never sees a `tool_call` chunk.
- SQLite path is `MESSAGE_DB_PATH` env var (default `messages.db` relative to the `server/` root). Use `/tmp/messages.db` in Docker.
- Do not move tool execution into a separate service.

## CustomLLM vendor

- Use the SDK's `CustomLLM` vendor (not `OpenAI`) for the LLM stage.
- Both `base_url` and `api_key` are required (`CustomLLM` rejects missing either).
- `CUSTOM_LLM_URL` must be a public URL — there is no localhost default by design.
- VAD (`turn_detection`) is set on `AgoraAgent(...)`, not on the vendor, because this recipe uses the cascading STT/LLM/TTS pipeline (`.with_stt().with_llm().with_tts()`).

## Web (TypeScript / Next.js)

- Lint/format with Biome (`bun run lint`, `bun run lint:fix` in `web/`).
- RTC client creation must be StrictMode-safe (strict mode is on).
- Transcript speaker mapping uses real UIDs (`normalizeTranscript` maps `uid === '0'` to the local UID); do not heuristically guess speakers.
- API client lives in `src/services/api.ts`; UI never calls `fetch` to the backend directly.

## Testing approach

- Backend: `pytest` in `server/`, standalone — `conftest.py` fakes env and SDK session, so no cloud or real creds are needed. Four test files cover: tool logic, LLM endpoint contract, mount + Agora-free assertion, and agent construction.
- Web: contract/proxy/fastapi/llm smoke scripts under `web/scripts/` run without live Agora calls.
- Run the **narrowest** relevant verify command before finishing (see [05_workflows](05_workflows.md)).

## Doc upkeep

When you change request/response contracts, env vars, or workflow, update the web client, backend, contract checks, README, **and** the matching `docs/ai/L1/` file together, then bump `Last Reviewed` in [L0](../L0_repo_card.md).

## Related Deep Dives

- None.
