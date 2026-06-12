# Agora Conversational AI — Tool Calling Recipe (Python)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Python](https://img.shields.io/badge/python-%3E%3D3.10-blue)](https://www.python.org/)
[![Bun](https://img.shields.io/badge/bun-latest-black)](https://bun.sh/)

The **tool-calling** recipe in the Agora Conversational AI recipes family. Bring
your own LLM endpoint to Agora's voice pipeline and add tool execution to it:
the agent's LLM stage is pointed at your own OpenAI-compatible
`POST /chat/completions` endpoint, which internally runs tools — `log_message`
to save a note and `list_messages` to read your notes back — when the user's
intent warrants it, and streams back only the final spoken reply. Notes persist
in a small SQLite database, so they survive restarts. Agora cloud never sees a
`tool_call` — the tool loop is entirely inside `server/src/llm.py`. STT
(Deepgram nova-3) and TTS (MiniMax) stay Agora-managed.

This repo ships a **zero-key mock** LLM endpoint so you can run the full
STT → tool-calling LLM → TTS pipeline immediately, then replace the mock with
your own model and tool registry.

## Prerequisites

- [Python 3.10+](https://www.python.org/)
- [Bun](https://bun.sh/)
- [Agora CLI](https://github.com/AgoraIO/cli) — makes generating an App ID + App Certificate easy
- [ngrok](https://ngrok.com/) — the backend must be publicly reachable so Agora cloud can call `/llm`

## Run It

```bash
# 1. Install + create the server Python venv
bun run setup

# 2. Add Agora credentials (CLI), or edit server/.env.local by hand
agora login
agora project use <your-project>          # select which project to use (you may have several)
agora project env write server/.env.local # writes App ID/Certificate; keeps your CUSTOM_LLM_* lines

# 3. Expose the backend publicly (Agora cloud calls /llm/chat/completions)
ngrok http 8000

# 4. Add the tunnel URL to server/.env.local (use whatever domain ngrok prints —
#    today that is usually *.ngrok-free.dev)
#    CUSTOM_LLM_URL=https://<your-tunnel>.ngrok-free.dev/llm/chat/completions

# 5. Run the backend and web
bun run dev
```

Open [http://localhost:3000](http://localhost:3000) → **Start Conversation** → speak.

### Working from a clone

If you cloned this repo (rather than scaffolding via the Agora CLI), the steps
above are complete as written: `bun run setup` creates the server Python venv
and installs web dependencies, then `bun run dev` brings up the backend and web.
You still need Agora credentials in `server/.env.local` and a public
`CUSTOM_LLM_URL` tunnel before a conversation can connect.

Services:

- Frontend — http://localhost:3000
- Backend — http://localhost:8000 (also serves `/llm`)
- API docs — http://localhost:8000/docs

## Deploy

Deploy `web` (Next.js) and `server` (a single publicly reachable FastAPI
backend). The mock LLM endpoint is mounted at `/llm` in the same process, so
Agora cloud reaches it at `<public-url>/llm/chat/completions`. Set
`AGENT_BACKEND_URL` in the web deployment so the Next rewrites reach the
backend.

A single-process Docker image is published to
`ghcr.io/AgoraIO-Conversational-AI/recipe-agent-tool-calling` on `v*` tags.
It bundles the agent backend and the mock LLM endpoint in one process on
port 8000. Point `CUSTOM_LLM_URL` at `<public-url>/llm/chat/completions`.

> **Co-public caveat:** the server :8000 is now the public endpoint Agora calls
> (`/llm`), so the token endpoints are co-public; the App Certificate is only
> used in-memory to mint tokens (never on the wire); add auth/rate-limiting
> before a real deployment.

## Environment variables

Backend env file: [`server/.env.example`](server/.env.example).

| Variable | Required | Default | Notes |
| --- | :---: | :---: | --- |
| `AGORA_APP_ID` | ✅ | — | Agora Console → Project → App ID |
| `AGORA_APP_CERTIFICATE` | ✅ | — | Agora Console → Project → App Certificate (server only) |
| `CUSTOM_LLM_URL` | ✅ | — | **Public** chat-completions URL of your mounted `/llm` endpoint (`<tunnel>/llm/chat/completions`). Agora cloud calls it; cannot be `localhost`. |
| `CUSTOM_LLM_API_KEY` | ✅ | `any-key-here` | Forwarded by Agora cloud as `Authorization: Bearer`. Required by the `CustomLLM` vendor. |
| `CUSTOM_LLM_MODEL` |  | `tool-mock` | Model name passed to your endpoint |
| `AGENT_GREETING` |  | built-in | Optional opening line override |
| `PORT` |  | `8000` | Agent backend port |
| `MESSAGE_DB_PATH` |  | `messages.db` | SQLite file the tool loop stores notes in. Optional; defaults relative to `llm/` legacy path. Set to `/tmp/messages.db` in Docker. |
| `AGENT_BACKEND_URL` (web deploy) | ✅ | — | Required in a deployed `web` app when proxying to the backend |

## Commands

```bash
bun run setup            # install web deps + create server/ venv
bun run dev              # run backend (:8000, serves /llm) + web (:3000)

bun run doctor           # prerequisite check (no creds needed)
bun run doctor:local     # + .env.local + credentials + CUSTOM_LLM_URL checks

bun run verify           # web-only gate (no Agora creds needed)
bun run verify:local     # full local gate: backend compile + smoke tests + web build
bun run clean            # remove venvs and build artifacts
```

Tests run standalone (no Agora cloud needed): `pytest` in `server/`, plus
`bun run verify` in `web/`. CI runs them on Linux/macOS/Windows × Python 3.10 & 3.13.

## Architecture

```
Browser (localhost:3000)
  │  fetch /api/*
  ▼
Next.js  ──rewrite──▶  Agent backend  (server/, localhost:8000)
                          │  starts agent session (CustomLLM vendor)
                          ▼
                       Agora ConvoAI Cloud
                          │  POST <CUSTOM_LLM_URL>   (Authorization: Bearer)
                          ▼
                       Tool-calling LLM endpoint  (mounted at /llm in server/, localhost:8000)
                          ▲  public via ngrok tunnel
                          │  runs log_message / list_messages (SQLite), streams reply
```

The browser only ever calls Next `/api/*`, which rewrites to the agent backend.
The agent backend owns Agora tokens and agent lifecycle. The **tool-calling LLM
endpoint** is mounted at `/llm` in the same backend; because Agora cloud — not
the browser — calls it, the backend must be publicly reachable (`ngrok http 8000`).
See [ARCHITECTURE.md](./ARCHITECTURE.md).

## Repo Map

- `web/` — Next.js frontend (:3000); RTC/RTM lifecycle and UI.
- `server/` — FastAPI agent backend (:8000); Agora tokens + agent lifecycle, `CustomLLM` vendor, and the `/llm` endpoint mounted at the same port.
  - `server/src/llm.py` — OpenAI-compatible mock `/chat/completions` handler; internal `log_message` / `list_messages` tool loop over SQLite; no Agora deps.
- `ARCHITECTURE.md` — system shape and component boundaries.
- `AGENTS.md` — guide for coding agents working in this repo.

## What You Get

- A **Next.js** web client (:3000) that drives the RTC/RTM lifecycle and only
  ever calls `/api/*`.
- A **FastAPI** agent backend (:8000) that owns Agora token generation and the
  agent session lifecycle.
- The `/api/get_config` · `/api/startAgent` · `/api/stopAgent` contract between
  the web client and the backend (Next rewrites, no Route Handlers).
- An internal **tool loop** — `log_message` / `list_messages` over SQLite —
  that streams only the spoken reply back to Agora (Agora never sees a
  `tool_call`).
- A **zero-key mock** LLM endpoint so the full pipeline runs with no LLM API key.

## How It Works

1. The browser calls `/api/get_config`, which Next rewrites to the backend; the
   backend mints an Agora token from `AGORA_APP_ID` + `AGORA_APP_CERTIFICATE`.
2. The browser joins the RTC channel, then calls `/api/startAgent`; the backend
   starts an agent session using the `CustomLLM` vendor pointed at
   `CUSTOM_LLM_URL`.
3. The user speaks. Agora runs STT (Deepgram nova-3), then sends the transcript
   to your `/llm` endpoint as an OpenAI `POST /chat/completions` request,
   forwarding `CUSTOM_LLM_API_KEY` as `Authorization: Bearer`.
4. Inside the endpoint, `run_agent_turn()` decides whether the turn warrants a
   tool. It runs `log_message()` to persist a note or `list_messages()` to read
   notes back from SQLite, then streams **only** the final spoken reply in the
   OpenAI SSE chunk format.
5. Agora runs TTS (MiniMax) on the streamed reply and plays it back in the
   channel. Agora cloud never observes the internal `tool_call` loop.
6. `/api/stopAgent` ends the session.

### Replacing the mock

Edit `run_agent_turn()` / `log_message()` / `list_messages()` in
[`server/src/llm.py`](server/src/llm.py). The endpoint must keep speaking the
OpenAI streaming `/chat/completions` contract. A production endpoint should also
validate the `Authorization: Bearer` header.

## Troubleshooting

| Problem | Fix |
| --- | --- |
| Agent starts but never speaks | `CUSTOM_LLM_URL` is not public or omits `/llm/chat/completions`. Use your ngrok URL. |
| `doctor:local` warns about localhost | Replace the local URL with your public tunnel URL. |
| Local calls fail / hang under a global proxy (Clash, etc.) | Your proxy is routing loopback through itself. Configure it to send `127.0.0.1`, `localhost`, and RFC-1918 ranges DIRECT (don't disable the proxy entirely). |
| `Missing server/venv` during verify | Run `bun run setup`. |

## More Docs

- [ARCHITECTURE.md](./ARCHITECTURE.md)
- [AGENTS.md](./AGENTS.md)

## License

Released under the [MIT License](./LICENSE).
