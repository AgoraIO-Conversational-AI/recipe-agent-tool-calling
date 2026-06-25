# recipe-agent-tool-calling — Repo Card

> Next.js web client + Python FastAPI backend for an Agora Conversational AI voice agent. The LLM stage is driven by a `CustomLLM` vendor pointing at an in-process OpenAI-compatible endpoint that runs an internal tool loop (log/recall notes over SQLite). STT (Deepgram nova-3) and TTS (MiniMax) remain Agora-managed.

## Identity

| Field          | Value                                                                           |
| -------------- | ------------------------------------------------------------------------------- |
| Repo           | `AgoraIO-Conversational-AI/recipe-agent-tool-calling`                           |
| Type           | `distributed-system` (single repo, two co-located processes)                   |
| Language       | Python 3.10+ (FastAPI + uvicorn) backend + Next.js 16 / React 19 web           |
| Deploy Target  | `web/` as Next.js app, `server/` as a single publicly reachable FastAPI service |
| Owner          | Agora Conversational AI DevEx                                                   |
| Last Reviewed  | 2026-06-25                                                                      |
| Recipe Role    | `base`                                                                          |
| Recipe Version | `1.0.0`                                                                         |
| Recipe Status  | `experimental`                                                                  |

## L1 — Summaries

The Audience column helps agents prioritise: **Use** = consuming the recipe's behavior, **Maintain** = modifying internals.

| File                                     | Purpose                                                                          | Audience       |
| ---------------------------------------- | -------------------------------------------------------------------------------- | -------------- |
| [01_setup](L1/01_setup.md)               | bun + venv + pip setup, env vars (incl. required `CUSTOM_LLM_URL`), ngrok step  | Use & Maintain |
| [02_architecture](L1/02_architecture.md) | Two-concern topology, tool loop vs MCP distinction, request lifecycle            | Maintain       |
| [03_code_map](L1/03_code_map.md)         | `web/` and `server/` trees with key file responsibilities                        | Maintain       |
| [04_conventions](L1/04_conventions.md)   | Python async + FastAPI patterns, Biome, JSON envelope, tool loop ownership       | Maintain       |
| [05_workflows](L1/05_workflows.md)       | Add a route, replace the mock LLM, add a tool, adjust session params, deploy    | Use            |
| [06_interfaces](L1/06_interfaces.md)     | FastAPI route contracts, rewrites, env vars, `CustomLLM` + LLM endpoint config  | Use & Maintain |
| [07_gotchas](L1/07_gotchas.md)           | `CUSTOM_LLM_URL` must be public, no localhost default, `PORT` in env, CORS      | Maintain       |
| [08_security](L1/08_security.md)         | Token007, App Certificate server-only, bearer forwarding, CORS, co-public risk  | Maintain       |

## Recipe Profile

This repo declares `Recipe Role: base`. See [RECIPE.md](RECIPE.md) for extension points, invariants, and stable contracts before changing reusable surfaces.
