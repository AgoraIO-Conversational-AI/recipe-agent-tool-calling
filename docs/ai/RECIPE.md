---
recipe_version: 1.0.0
recipe_status: experimental
extension_points:
  - id: api.routes
    name: Browser-facing API routes
  - id: agent.llm-config
    name: CustomLLM vendor model, greeting, max_history, and session parameters
  - id: llm.tool-loop
    name: Tool definitions, SQLite schema, and run_agent_turn routing logic
  - id: web.conversation-ui
    name: Conversation UI panels and controls
  - id: verification.contracts
    name: Contract, proxy, FastAPI, and LLM smoke verification
invariants:
  - id: api.rewrite-boundary
    summary: Browser calls stay on /api/* and Next rewrites to FastAPI; no Route Handlers for agent/token logic.
  - id: secrets.server-only
    summary: Agora App Certificate stays in the Python backend; CUSTOM_LLM_API_KEY is forwarded by Agora cloud but never reaches the browser.
  - id: llm.agora-free
    summary: server/src/llm.py has no agora_agent import; it is the provider-agnostic part a developer replaces.
  - id: tool.endpoint-internal
    summary: Tool calls execute inside the LLM endpoint; Agora cloud never sees a tool_call chunk.
  - id: custom_llm_url.public
    summary: CUSTOM_LLM_URL must be a public URL; there is no localhost default.
  - id: token.uid-concrete
    summary: Backend resolves missing, zero, or negative UIDs before issuing an RTC+RTM token.
stable_contracts:
  - id: env.required
    summary: AGORA_APP_ID, AGORA_APP_CERTIFICATE, CUSTOM_LLM_URL, and CUSTOM_LLM_API_KEY are required; AGENT_BACKEND_URL is required by deployed web rewrites.
  - id: api.core-routes
    summary: GET /api/get_config, POST /api/startAgent, and POST /api/stopAgent remain the browser-facing contract.
  - id: llm.endpoint-routes
    summary: POST /llm/chat/completions (Agora-facing) and GET /llm/health remain the LLM endpoint contract.
  - id: response.envelope
    summary: Successful backend responses use { code, msg, data }.
  - id: llm.sse-format
    summary: The LLM endpoint streams OpenAI SSE (role chunk, content chunks, finish_reason stop, [DONE]) with stream=true required.
---

# Recipe Contract

This base recipe defines the reusable surface for a Python-backed Agora Conversational AI **tool-calling** quickstart: a cascading STT/LLM/TTS pipeline where the LLM stage is driven by an internal tool-calling endpoint, behind a Next.js web client.

## Recipe Role

- Role: `base` recipe (self-contained, clone-and-run; no `Extends` pin).
- Target audience: developers who want to add tool/function calling to an Agora voice agent using their own OpenAI-compatible LLM endpoint.
- Reuse model: clone, bind project, expose backend publicly (ngrok or deploy), set `CUSTOM_LLM_URL`, run, then customize the tool loop or swap in a real model.

## Recipe Scope

- Python FastAPI token generation and managed agent lifecycle (cascading `CustomLLM` + `DeepgramSTT` + `MiniMaxTTS` vendors).
- A provider-agnostic OpenAI-compatible LLM endpoint mounted at `/llm`, with an internal keyword-routed tool loop over SQLite (`log_message` / `list_messages`).
- Next.js browser UI with RTC audio, RTM transcript/metrics, connection status.
- Rewrite-only `/api/*` browser facade hiding backend placement.
- Contract, proxy, FastAPI, and LLM smoke verification that need no live Agora calls.
- A zero-key mock: the full STT → LLM → TTS pipeline runs with no external LLM API key.

## Baseline Implementation Guidance

Use this repo's source and progressive disclosure docs as the starting point, then customize. Do not recreate the Agora ConvoAI integration from memory — vendor schemas, SDK builder fields, token behavior, and RTM details drift. Copy verified patterns from this repo.

## Extension Points

| ID | Surface | How to extend | Required follow-up |
| -- | ------- | ------------- | ------------------ |
| `api.routes` | `server/src/server.py`, `web/next.config.ts`, `web/src/services/api.ts` | Add FastAPI route, add rewrite, add browser fetch helper. | Extend `web/scripts/verify-api-contracts.ts`; add proxy/fastapi coverage if it belongs in local verification. |
| `agent.llm-config` | `server/src/agent.py` | Change `CUSTOM_LLM_MODEL`, `greeting_message`, `max_history`, `max_tokens`, `temperature`, `top_p`, VAD config, or session parameters. | Run `verify:backend` + `pytest tests`; document new env in `server/.env.example` (never add `PORT`). |
| `llm.tool-loop` | `server/src/llm.py` | Replace `run_agent_turn()` with real model calls, add tool functions, or change the SQLite schema. | Run `pytest tests/test_tools.py tests/test_llm.py -v`; keep `llm.py` Agora-free. |
| `web.conversation-ui` | `web/src/components/*`, `web/src/lib/conversation.ts` | Customize pre-call, transcript, metrics, connection status, mic, or visualizer UI. | Preserve RTC/RTM lifecycle ownership and transcript UID normalization. |
| `verification.contracts` | `web/scripts/*.ts`, root `package.json` | Add checks for new browser/backend or LLM boundaries. | Keep checks runnable without live Agora credentials. |

## Invariants

- Browser code calls only `/api/get_config`, `/api/startAgent`, and `/api/stopAgent` for the default flow.
- Next.js owns `/api/*` through rewrites only; no `web/app/api/**/route.ts` for agent/token logic.
- FastAPI owns token generation, `AGORA_APP_CERTIFICATE`, and agent lifecycle.
- `server/src/llm.py` has no `agora_agent` import; it is provider-agnostic.
- Tool calls execute inside the LLM endpoint; only the final spoken reply is streamed to Agora.
- `CUSTOM_LLM_URL` must be a public URL; there is no localhost default.
- The backend issues one RTC+RTM-capable token for a concrete non-zero UID.

## Stable Contracts

| Contract | Stable shape |
| -------- | ------------ |
| Required backend env | `AGORA_APP_ID`, `AGORA_APP_CERTIFICATE`, `CUSTOM_LLM_URL`, `CUSTOM_LLM_API_KEY` |
| Optional backend env | `CUSTOM_LLM_MODEL`, `AGENT_GREETING`, `MESSAGE_DB_PATH`, `PORT` (env only) |
| Required web deploy env | `AGENT_BACKEND_URL` |
| `GET /api/get_config` | Query `channel?`, `uid?`; returns `data.app_id`, `data.token`, `data.uid`, `data.channel_name`, `data.agent_uid`. |
| `POST /api/startAgent` | Body `{ channelName, rtcUid, userUid, parameters? }`; returns `data.agent_id`, `data.channel_name`, `data.status`. |
| `POST /api/stopAgent` | Body `{ agentId }`; returns `{ code: 0, msg: "success" }`. |
| `POST /llm/chat/completions` | Body OpenAI `ChatCompletionRequest` with `stream: true`; returns OpenAI SSE. |
| Success envelope | `{ "code": 0, "msg": "success", "data": ... }` where the route has data. |
| Verification entry points | `bun run verify:web`, `bun run verify:backend`, `bun run verify:web:proxy`, `bun run verify:local:fastapi`, `bun run verify:local:llm`, `bun run verify:local`. |

## Internal / Subject to Change

- Visual layout, component composition, Tailwind classes, and assets under `web/src/components/`.
- Exact model name, voice, greeting text, and temperature, as long as they stay documented extension points.
- In-memory `Agent._sessions` details; the stable behavior is start by channel/user and stop by returned `agent_id`.
- Keyword triggers in `run_agent_turn()` and the specific SQLite schema; the stable behavior is log-on-request, recall-on-request.
- Verification internals under `web/scripts/`; the stable surface is the root script names and what they assert.
- `agora-agents` SDK minor-version behavior; this recipe lower-bounds `>=2.3.0` but does not freeze every field.

## Related Progressive Disclosure Docs

- `L1/01_setup.md` — setup, env, ngrok, and commands.
- `L1/02_architecture.md` — request flow and topology.
- `L1/05_workflows.md` — common modification workflows.
- `L1/06_interfaces.md` — route, rewrite, env, and vendor contracts.
- `L1/L2/tool_calling_flow.md` — full LLM endpoint, SSE format, and tool loop detail.
- `L1/L2/session_lifecycle.md` — RTC/RTM/session orchestration.
