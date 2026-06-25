# 07 · Gotchas

> Non-obvious pitfalls specific to the tool-calling recipe. Read before changing the agent, LLM endpoint, env, or verify scripts.

## `CUSTOM_LLM_URL` must be public — no localhost default

Agora cloud (not this backend) calls `/llm/chat/completions`. A `localhost` URL lets the agent "start" while LLM calls silently fail on Agora's side. There is intentionally no localhost default for `CUSTOM_LLM_URL`. Use ngrok or a deployed backend.

```
doctor:local warns about localhost → fix: use your public tunnel URL
```

## `CUSTOM_LLM_URL` is validated at `Agent.__init__`, not at startup

`Agent.__init__` raises `ValueError` if `CUSTOM_LLM_URL` (or `CUSTOM_LLM_API_KEY`) is missing. The server catches this at import time (`agent = None`). All three routes return 500 while `agent is None`. This means the server does **not** boot into a usable state without `CUSTOM_LLM_URL`.

## Both `CUSTOM_LLM_URL` and `CUSTOM_LLM_API_KEY` are required

The `CustomLLM` vendor rejects a missing `api_key`, and `base_url` is only valid with a key. Do not default `CUSTOM_LLM_API_KEY` to an empty string.

## No `PORT` in `server/.env.example`

`verify:local:fastapi` injects a random `PORT` and loads env with `load_dotenv(override=False)` in `llm.py` (but `override=True` in `server.py`). A `PORT` line in `.env.example` (copied to `.env.local`) can interfere with the injected port in the smoke test.

## Tool loop is keyword-based — order of recall vs log checks matters

`run_agent_turn()` checks recall triggers (`list`, `read back`, `what have i`, etc.) **before** log triggers (`log`, `note`, `record`, etc.). An utterance containing both (e.g., "what I have noted") routes to recall — by design. A real production endpoint would use model-driven tool-call detection instead.

## Agora cloud never sees a `tool_call` chunk

The tool loop completes fully inside `server/src/llm.py` before streaming. Only the final spoken text is sent as SSE chunks. Do not add `tool_calls` to the streamed response — Agora does not handle them.

## `llm.py` must stay Agora-free

`test_llm_mount.py` inspects `llm.py` via AST and fails if any `agora*` root import is found. Keep `server/src/llm.py` provider-agnostic.

## Keep `/api/*` ownership in rewrites

Adding `web/app/api/**/route.ts` for agent/token logic breaks the boundary — `verify-api-contracts.ts` explicitly fails if a `route.ts` exists under `app/api`. Token logic belongs in `server/`.

## camelCase request fields

`StartAgentRequest` uses `channelName`, `rtcUid`, `userUid` (camelCase) to match the browser client. Renaming one side without the other breaks the contract tests.

## Co-public endpoints in deploy

Once deployed, `/get_config`, `/startAgent`, and `/stopAgent` are publicly reachable on the same port as `/llm/chat/completions`. They are unauthenticated in this recipe. Add auth/rate-limiting (ingress, gateway, or proxy) before any real deployment.

## Local calls under a global proxy

Global proxies (Clash, etc.) can break `localhost`/RFC-1918 traffic. Configure the proxy to send `127.0.0.1`, `localhost`, and private ranges DIRECT, or use `socksio` (in `requirements.txt`) plus `all_proxy` to route the backend through SOCKS.

## Related Deep Dives

- [tool_calling_flow](L2/tool_calling_flow.md) — correct SSE streaming and tool routing.
