# 06 · Interfaces

> Boundary contracts: backend routes, the `/api/*` rewrite map, env vars, the response envelope, the `CustomLLM` vendor config, and the `/llm` endpoint contract.

## Backend routes (port 8000)

The browser calls the first three as `/api/<name>`; Next rewrites to the backend `/<name>`. Agora cloud calls `/llm/chat/completions` directly.

### `GET /get_config`

- Query (optional): `channel?: string`, `uid?: int` (≤ 0 or missing → backend generates one).
- Returns `data`: `{ app_id, token, uid (string), channel_name, agent_uid (string) }`.
- Token is a Token007 RTC+RTM token, expiry 3600s, for a concrete non-zero UID.

### `POST /startAgent`

- Body: `{ channelName: string, rtcUid: int, userUid: int, parameters?: object }`.
  - `parameters.output_audio_codec?: string` is the only honored parameter field.
- Returns `data`: `{ agent_id, channel_name, status: "started" }`.
- 400 if `AGORA_APP_ID`/`AGORA_APP_CERTIFICATE`/`CUSTOM_LLM_URL`/`CUSTOM_LLM_API_KEY` unset (raises at `Agent.__init__`), or `channelName`/`rtcUid`/`userUid` invalid.

### `POST /stopAgent`

- Body: `{ agentId: string }`.
- Returns `{ code: 0, msg: "success" }` (no `data`).

### `POST /llm/chat/completions`

- Agora cloud calls this with `Authorization: Bearer <CUSTOM_LLM_API_KEY>`.
- Body: OpenAI `ChatCompletionRequest` (`model`, `messages`, `stream: true`).
- Returns: OpenAI SSE chunks (`text/event-stream`). See [tool_calling_flow](L2/tool_calling_flow.md).
- 400 if `stream` is `false`.

### `GET /llm/health`

- Returns `{ status: "ok", service: "custom-llm-mock" }`.

## Response envelope

```json
{ "code": 0, "msg": "success", "data": { } }
```

`data` omitted when the route has no payload. Non-zero `code` or missing `data` = error on the client side.

## Rewrite map (`web/next.config.ts`)

| Browser path        | Backend destination |
| ------------------- | ------------------- |
| `/api/get_config`   | `/get_config`       |
| `/api/startAgent`   | `/startAgent`       |
| `/api/stopAgent`    | `/stopAgent`        |

`rewrites()` returns `[]` when `AGENT_BACKEND_URL` is unset. The contract is asserted by `verify-api-contracts.ts`.

## Browser API client (`web/src/services/api.ts`)

- `getConfig({ channel?, uid? }) → GetConfigResponse`
- `startAgent(channelName, rtcUid, userUid) → agent_id`
- `stopAgent(agentId) → void`

## Environment variables

| Variable                | Scope          | Required | Default               |
| ----------------------- | -------------- | :------: | --------------------- |
| `AGORA_APP_ID`          | backend        |    ✅    | —                     |
| `AGORA_APP_CERTIFICATE` | backend        |    ✅    | —                     |
| `CUSTOM_LLM_URL`        | backend        |    ✅    | — (must be public)    |
| `CUSTOM_LLM_API_KEY`    | backend        |    ✅    | `any-key-here`        |
| `CUSTOM_LLM_MODEL`      | backend        |          | `tool-mock`           |
| `AGENT_GREETING`        | backend        |          | built-in line         |
| `MESSAGE_DB_PATH`       | backend        |          | `messages.db` (server root) |
| `AGENT_BACKEND_URL`     | web (deploy)   |   ✅\*   | `http://localhost:8000` (dev) |
| `PORT`                  | backend (env only) |      | `8000` — do **not** put in `.env.example` |

\* Required wherever the web app is deployed; rewrites are empty without it.

## `CustomLLM` vendor config (`agent.py`)

`CustomLLM(base_url, api_key, model, greeting_message, failure_message, max_history, max_tokens, temperature, top_p)` produces a vendor whose wire config sets `vendor: "custom"`.

The cascading pipeline is built as:

```python
agora_agent.with_stt(stt).with_llm(llm).with_tts(tts)
```

- STT: `DeepgramSTT(model="nova-3", language="en")`
- TTS: `MiniMaxTTS(model="speech_2_6_turbo", voice_id="English_captivating_female1")`
- VAD (`turn_detection`) is set on `AgoraAgent(...)`, not on the vendor.

## Related Deep Dives

- [tool_calling_flow](L2/tool_calling_flow.md) — full `/llm` endpoint contract, SSE format, and tool routing.
