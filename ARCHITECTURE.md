# Architecture — Tool Calling Recipe

Two processes. The browser talks only to Next.js `/api/*`, which rewrites to the
agent backend. The agent backend owns Agora tokens and agent lifecycle, and also
serves the tool-calling LLM endpoint mounted at `/llm`, which **Agora cloud**
calls directly.

## Request flow

```
Browser
  │  GET /api/get_config            → token + channel/UIDs
  │  POST /api/startAgent           → start agent session
  ▼
Next.js  (rewrites /api/* → AGENT_BACKEND_URL)
  ▼
Agent backend (server/, :8000)
  │  builds session with CustomLLM(base_url=CUSTOM_LLM_URL)
  ▼
Agora ConvoAI Cloud
  │  user speech → Deepgram STT (managed)
  │  POST <CUSTOM_LLM_URL>/chat/completions   (Authorization: Bearer <key>)
  ▼
Tool-calling LLM endpoint (mounted at /llm in server/, :8000, public via tunnel)
  │  runs internal tool loop; returns OpenAI SSE (spoken text only)
  ▼
Agora ConvoAI Cloud → MiniMax TTS (managed) → user hears speech
                     → RTM transcript / metrics → web UI
```

`POST /api/stopAgent { agentId }` ends the session.

## One process, two concerns

`server/` runs a single process that serves both the token/agent endpoints and,
mounted at `/llm`, the OpenAI-compatible tool-calling LLM endpoint
(`server/src/llm.py`).

The two concerns are kept in separate files with a one-directional dependency
(`server.py` imports `llm`, never the reverse), and `llm.py` has no `agora_agent`
import — it is the provider-agnostic part you replace with your own model and
tool registry.

Merging them onto one public surface is a deliberate trade. The Agora App
Certificate is only ever used in-memory to mint tokens — it never crosses a wire —
so co-locating the public `/llm` route with the token endpoints does not expose
the certificate. It does, however, make the token-minting endpoints
(`/get_config`, `/startAgent`, `/stopAgent`) publicly reachable. They are
unauthenticated in this recipe; put auth / rate-limiting in front of them
(ingress, gateway, or a proxy) before any real deployment.

## Where the tool runs

In this recipe the tool calls are handled entirely inside `server/src/llm.py`,
which owns a small SQLite message log. `run_agent_turn()` detects the user's
intent and executes one of two tools internally — `log_message()` to persist a
note, or `list_messages()` to read recent notes back (recall is checked before
logging, so "what have I noted" reads back instead of saving). Only the final
spoken reply is streamed; Agora cloud never sees a `tool_call` chunk. Because the
notes live in SQLite, they survive an endpoint restart.

This is distinct from an MCP-orchestrated approach, where Agora cloud would invoke
a separate MCP server to run tools. That pattern is a separate recipe
(`recipe-agent-mcp`), not built here.

## API (agent backend, port 8000)

| Endpoint | Method | Description |
| --- | --- | --- |
| `/get_config` | GET | Token + channel/UID config |
| `/startAgent` | POST | Start the agent session |
| `/stopAgent` | POST | Stop the agent by `agent_id` |
| `/llm/chat/completions` | POST | OpenAI-compatible completions (tool loop) |
| `/llm/health` | GET | LLM endpoint health check |

The browser calls the first three as `/api/*`; Next rewrites them to
`AGENT_BACKEND_URL`. Agora cloud calls `/llm/chat/completions` directly.

## Auth

- Browser → agent backend: none (local dev).
- Agent backend → Agora cloud: Token007, generated from `AGORA_APP_ID` +
  `AGORA_APP_CERTIFICATE`.
- Agora cloud → tool-calling LLM endpoint: `Authorization: Bearer <CUSTOM_LLM_API_KEY>`.
  The mock endpoint does not validate it; a production endpoint should.
