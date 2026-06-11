# Tool-Calling LLM Endpoint — Mock

An OpenAI-compatible `POST /chat/completions` server (port 8001) that Agora cloud
calls during a conversation. This mock demonstrates internal tool execution: it
detects the user's intent, runs the `log_message` tool inside the endpoint, and
streams back only the spoken confirmation — all with **no LLM API key**.

It has no `agora-agents` dependency — it is a plain FastAPI app, which is exactly
the boundary you replace with your own model and tool registry.

## The contract

Implement `POST /chat/completions` returning OpenAI-style SSE:

- first chunk sets `delta.role = "assistant"`
- content chunks carry `delta.content`
- a final chunk sets `finish_reason = "stop"`
- the stream terminates with `data: [DONE]`

Only streaming (`stream: true`) is supported; non-streaming requests return 400.

## Run

```bash
cd llm
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python src/custom_llm_server.py     # serves on CUSTOM_LLM_PORT (default 8001)
```

## Expose it publicly

Agora cloud — not the browser — calls this server, so it must be reachable from
the public internet. For local dev, tunnel it:

```bash
ngrok http 8001
```

Then set `CUSTOM_LLM_URL=https://<tunnel>/chat/completions` in `server/.env.local`.

## Auth

This mock does **not** authenticate. A production endpoint should validate the
`Authorization: Bearer <CUSTOM_LLM_API_KEY>` header that Agora cloud forwards
(the key you set on the agent backend).

## Replace the mock

Edit `get_mock_response()` in `src/custom_llm_server.py`. Examples: call a local
model (Ollama/vLLM), inject RAG context before generating, or route models by
content.

This mock also demonstrates internal tool execution: `run_agent_turn()` decides
whether to call `log_message()` and streams the confirmation. A real endpoint
would run the OpenAI tool-call loop against your model.
