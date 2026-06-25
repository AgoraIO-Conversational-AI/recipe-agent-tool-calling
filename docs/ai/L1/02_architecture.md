# 02 · Architecture

> One process, two concerns. The browser talks only to Next.js `/api/*`, which rewrites to the FastAPI backend. The backend owns Agora tokens and agent lifecycle, and also hosts the tool-calling LLM endpoint at `/llm` — the surface Agora cloud calls directly.

## Topology

```
Browser (localhost:3000)
  │  fetch /api/*
  ▼
Next.js (web/)  ──rewrite──▶  Agent backend (server/, :8000)
                                 │  builds session with CustomLLM(base_url=CUSTOM_LLM_URL)
                                 ▼
                              Agora ConvoAI Cloud
                                 │  user speech → Deepgram STT (managed)
                                 │  POST <CUSTOM_LLM_URL>/chat/completions (Authorization: Bearer)
                                 ▼
                              Tool-calling LLM endpoint (server/src/llm.py, mounted at /llm)
                                 │  internal tool loop: log_message / list_messages (SQLite)
                                 │  streams only the spoken reply (OpenAI SSE)
                                 ▼
                              Agora ConvoAI Cloud → MiniMax TTS (managed) → user hears speech
                              RTM transcript / metrics → web UI
```

- **`web/`** — Next.js 16 / React 19 / TypeScript. Owns UI plus the RTC/RTM client lifecycle. Calls only `/api/*`.
- **`server/`** — Python FastAPI (:8000). Owns Agora token generation and agent session lifecycle. SDK: `agora-agents>=2.3.0` (`import agora_agent`).
- **`server/src/llm.py`** — Provider-agnostic OpenAI-compatible endpoint mounted at `/llm`. No `agora_agent` import. Internally runs `run_agent_turn()` → `log_message()` / `list_messages()` over SQLite before streaming the spoken reply.

## One process, two concerns

`server/src/server.py` mounts `llm_app` (from `llm.py`) at `/llm`:

```python
app.mount("/llm", llm_app)
```

This keeps a single port (:8000) public. Because Agora cloud — not the browser — calls `/llm/chat/completions`, the backend **must** be publicly reachable (ngrok or deployed). The dependency is one-directional: `server.py` imports `llm`, never the reverse.

## Request lifecycle

1. Browser `GET /api/get_config` → Next rewrites to backend `/get_config`; backend mints a Token007 from `AGORA_APP_ID` + `AGORA_APP_CERTIFICATE` and returns channel + UIDs.
2. Browser joins the RTC channel, then `POST /api/startAgent`; backend builds a `CustomLLM` vendor (pointing at `CUSTOM_LLM_URL`) and starts an async cascading session: STT (Deepgram nova-3) → CustomLLM → TTS (MiniMax).
3. User speaks. Agora runs STT and posts to `CUSTOM_LLM_URL/chat/completions` with `Authorization: Bearer <CUSTOM_LLM_API_KEY>`.
4. Inside the endpoint, `run_agent_turn()` routes by keyword: recall (`list_messages`) or log (`log_message`), then streams only the final spoken reply in OpenAI SSE format. Agora never sees a `tool_call` chunk.
5. TTS (MiniMax) converts the reply to speech; RTM delivers transcript + metrics to the web UI.
6. `POST /api/stopAgent { agentId }` ends the session.

## Why the tool loop is inside the endpoint

The tool calls execute inside `server/src/llm.py`, entirely hidden from Agora cloud. Only the final spoken text crosses the wire to Agora. This is distinct from the MCP pattern (`recipe-agent-mcp`), where Agora cloud would invoke a separate MCP server. In this recipe the loop is intentionally self-contained and replaceable.

## Key abstractions

- **`Agent`** (`server/src/agent.py`) — async wrapper around `AgoraAgent`; owns the `AsyncAgora` client, `CustomLLM`/`DeepgramSTT`/`MiniMaxTTS` vendor chain, and the in-memory `_sessions` map keyed by `agent_id`.
- **`run_agent_turn()`** (`server/src/llm.py`) — keyword-based router; executes `log_message` or `list_messages` against a SQLite DB and returns the spoken reply string.
- **Rewrite proxy** (`web/next.config.ts`) — the only browser→backend boundary; no Next Route Handlers exist for agent/token logic.

## Tech decisions

- **Rewrites, not Route Handlers** — hides backend placement behind `/api/*`.
- **CustomLLM vendor** — the SDK's `CustomLLM` sets `vendor: "custom"` and requires both `base_url` and `api_key`; no localhost default by design.
- **VAD on `AgoraAgent`** — turn detection (`speech_threshold`, `vad_config`) is set directly on `AgoraAgent(...)`, not on the vendor, because this recipe uses the cascading STT/LLM/TTS pipeline (not `.with_mllm()`).
- **SQLite persistence** — notes survive restarts; path configurable via `MESSAGE_DB_PATH`.

## Related Deep Dives

- [tool_calling_flow](L2/tool_calling_flow.md) — internal tool loop, SSE format, and the keyword-routing logic.
- [session_lifecycle](L2/session_lifecycle.md) — browser orchestration of config + start/stop, RTC/RTM, transcript mapping.
