# 08 · Security

> Trust boundaries, secret handling, and auth for the tool-calling recipe.

## Trust boundaries

| Hop                                      | Auth                                                                             |
| ---------------------------------------- | -------------------------------------------------------------------------------- |
| Browser → agent backend                  | None in local dev (the `/api/*` rewrite is same-origin).                         |
| Agent backend → Agora cloud              | Token007, generated from `AGORA_APP_ID` + `AGORA_APP_CERTIFICATE`.              |
| Agora cloud → tool-calling LLM endpoint  | `Authorization: Bearer <CUSTOM_LLM_API_KEY>`. The mock does **not** validate it; a production endpoint should. |

## Secret handling

- **Server-only secrets:** `AGORA_APP_CERTIFICATE` lives only in `server/.env.local` and is used only in-memory to mint tokens — it never crosses a wire.
- `CUSTOM_LLM_API_KEY` is forwarded by Agora cloud to the `/llm` endpoint; it does not reach the browser.
- `server/.env.local` is gitignored; `server/.env.example` ships placeholders only.
- Tokens (`generate_convo_ai_token`) expire after 3600s and are minted per `get_config` call for a concrete non-zero UID.

## CORS

The backend (`server.py`) and the LLM endpoint (`llm.py`) both set `CORSMiddleware` with `allow_origins=["*"]` — open by design for a local/dev recipe. **Lock this down to known origins before any production deployment.**

## Validation

- `Agent.__init__()` raises `ValueError` and sets `agent = None` if any required env var is missing; all routes return 500 while `agent is None`.
- `Agent.start()` rejects empty `channel_name` and non-positive `agent_uid`/`user_uid` before issuing tokens or starting a session.
- Route errors are sanitized: `_log_route_error` logs only non-`None` context; exceptions map to 400/500 without leaking internals beyond the message.

## Co-public risk

Because the agent backend and the `/llm` endpoint share a single port, deploying the backend publicly (required for Agora to call `/llm/chat/completions`) also makes the token endpoints (`/get_config`, `/startAgent`, `/stopAgent`) publicly reachable and unauthenticated. Mitigate with:

- An ingress or reverse proxy that restricts `/get_config`, `/startAgent`, `/stopAgent` to known origins.
- Rate limiting on the token endpoints.
- Validating `Authorization: Bearer` in the `/llm/chat/completions` handler for production use.

## Deployment notes

- Set `AGENT_BACKEND_URL` only to a backend you control; the rewrite forwards browser requests there verbatim.
- The published Docker image is backend-only (`:8000`); it does not bundle secrets.
- Set `MESSAGE_DB_PATH=/tmp/messages.db` (or another writable path) in Docker — do not use the default relative path inside a container.

## Related Deep Dives

- None.
