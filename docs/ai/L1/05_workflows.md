# 05 · Workflows

> Step-by-step guides for the common changes in this recipe. Each ends with the narrowest verify command to run.

## Add or change a browser-facing route

1. Add the FastAPI handler in `server/src/server.py` (return the `{ code, msg, data }` envelope).
2. Add the `/api/<name>` → `/<name>` mapping in `web/next.config.ts` `rewrites()`.
3. Add a client helper in `web/src/services/api.ts`.
4. Extend `web/scripts/verify-api-contracts.ts` with the new path + envelope assertions.
5. Verify: `bun run verify:web` (and `bun run verify:local:fastapi` if it should go through the real backend).

## Replace the mock LLM with your own model

1. Edit `run_agent_turn()` in `server/src/llm.py`. Keep the OpenAI SSE streaming contract (role chunk → content chunks → `finish_reason: stop` → `[DONE]`).
2. Update `log_message()` / `list_messages()` or add your own tool registry as needed.
3. If you add a real LLM API key, add it to `server/.env.example` and document it.
4. Keep `llm.py` free of `agora_agent` imports.
5. Verify: `cd server && pytest tests -v` + `bun run verify:local:llm`.

## Add a tool to the loop

1. Write the tool function in `server/src/llm.py`.
2. Add trigger keywords (or replace the heuristic with a model-based tool-call parse).
3. Call the tool in `run_agent_turn()`; ensure only the final spoken reply is returned.
4. Add a test in `server/tests/test_tools.py`.
5. Verify: `cd server && pytest tests -v`.

## Change the agent greeting or model name

1. Greeting: set `AGENT_GREETING` (env) or edit the default in `server/src/agent.py`.
2. Model: set `CUSTOM_LLM_MODEL` (default `tool-mock`); the value is passed to the endpoint.
3. Verify: `bun run verify:backend`.

## Adjust session parameters (codec, scenario)

1. Edit the `parameters` dict in `Agent.start()` (`audio_scenario`, `data_channel`, `enable_metrics`, etc.). `output_audio_codec` is also accepted per-request via `parameters` on `POST /startAgent`.
2. Verify: `bun run verify:local:fastapi`.

## Run / debug locally

```bash
bun run dev              # both processes + tunnel required for agent to call /llm
bun run doctor:local     # check creds + .env.local + CUSTOM_LLM_URL before a live call
```

## Verify before finishing

| Change touches…              | Run                                                                        |
| ---------------------------- | -------------------------------------------------------------------------- |
| Web only                     | `bun run verify:web`                                                        |
| Backend logic / agent config | `bun run verify:backend` + `cd server && pytest tests -v`                  |
| Tool loop / LLM endpoint     | `cd server && pytest tests -v` + `bun run verify:local:llm`                |
| Route/proxy boundary         | `bun run verify:web:proxy` and/or `bun run verify:local:fastapi`           |
| Anything end-to-end (local)  | `bun run verify:local`                                                      |

## Deploy

1. Deploy `server/` as a **publicly reachable** FastAPI service (it serves both the agent endpoints and `/llm`).
2. Set `CUSTOM_LLM_URL=<public-url>/llm/chat/completions` in the backend env.
3. Deploy `web/` as a Next.js app; set `AGENT_BACKEND_URL` so rewrites reach the backend.
4. The published Docker image is `ghcr.io/AgoraIO-Conversational-AI/recipe-agent-tool-calling` on `v*` tags — single process, port 8000.

> **Note:** Once deployed, the token endpoints (`/get_config`, `/startAgent`, `/stopAgent`) are also publicly reachable on the same port. Add auth/rate-limiting before any real deployment. See [08_security](08_security.md).

## Related Deep Dives

- [tool_calling_flow](L2/tool_calling_flow.md) — SSE contract, tool routing internals.
- [session_lifecycle](L2/session_lifecycle.md) — client-side join/renewal/teardown.
