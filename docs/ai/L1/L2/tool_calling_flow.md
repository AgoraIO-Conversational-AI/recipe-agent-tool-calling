# Deep Dive — Tool Calling Flow

> **When to Read This:** You are changing the LLM endpoint, adding or modifying tools, debugging SSE streaming, or replacing the mock with a real model. For the high-level picture, start at [02_architecture](../02_architecture.md).

This recipe implements tool/function calling entirely inside `server/src/llm.py`, hidden from Agora cloud. The endpoint speaks the OpenAI Chat Completions streaming contract; the internal tool loop is invisible to Agora.

## The endpoint

`POST /chat/completions` is the only route Agora cloud calls. It is mounted in the server app at `/llm`, so Agora reaches it at `<CUSTOM_LLM_URL>` (e.g. `https://<tunnel>/llm/chat/completions`).

Key constraint: Agora always uses `stream: true`. Non-streaming requests are rejected with 400.

```python
@app.post("/chat/completions")
async def chat_completions(request: ChatCompletionRequest, authorization: ...):
    if not request.stream:
        raise HTTPException(status_code=400, detail="Only streaming mode is supported.")
    conn = get_db()
    try:
        response_text = run_agent_turn(conn, request.messages)
    finally:
        conn.close()
    return StreamingResponse(generate(), media_type="text/event-stream")
```

The DB work fully materializes `response_text` before the streaming generator runs — the generator never touches the DB.

## The tool loop

`run_agent_turn(conn, messages)` is the entry point. It extracts the last user message and routes by keyword:

```
recall triggers: "list", "read back", "remind me", "what have i", "what i have",
                 "what did i", "show me my", "my notes"
log triggers:    "log", "print", "note", "record", "console"
```

Recall is checked **before** log, so "what I have noted" reads back rather than logs. If neither trigger matches, a guidance message is returned.

| User intent           | Tool called       | SQLite operation           | Reply                                   |
| --------------------- | ----------------- | -------------------------- | --------------------------------------- |
| "log this: buy milk"  | `log_message`     | `INSERT INTO messages`     | `Logged your message: "buy milk". Anything else?` |
| "list my notes"       | `list_messages`   | `SELECT … ORDER BY created_at DESC LIMIT 10` | "You have 2 logged messages: …"         |
| Neither               | none              | none                       | Guidance message                        |

`log_message` strips the text after `:` if present; otherwise logs the full utterance.

## SQLite persistence

```python
DB_PATH = os.getenv("MESSAGE_DB_PATH") or os.path.join(_base_dir, "messages.db")

def get_db(path: str = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.execute("""CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        text TEXT NOT NULL,
        created_at REAL NOT NULL
    )""")
    conn.commit()
    return conn
```

A fresh connection is created and closed per request. Messages survive endpoint restarts because they are persisted to disk. `test_tools.py::test_persistence_across_connections` verifies this.

## SSE streaming contract

Agora ConvoAI Engine expects the exact OpenAI SSE format:

1. First chunk: role delta `{"role": "assistant", "content": ""}`.
2. Content chunks: one per word, `{"content": "<word>"}` with `delta`, 50 ms delay.
3. Final chunk: `{"content": "", "finish_reason": "stop"}`.
4. Terminator: `data: [DONE]`.

```python
async def generate():
    yield make_role_chunk(chunk_id, model)
    for i, word in enumerate(words):
        token = word if i == 0 else f" {word}"
        yield make_chunk(chunk_id, model, token)
        await asyncio.sleep(0.05)
    yield make_chunk(chunk_id, model, "", finish_reason="stop")
    yield "data: [DONE]\n\n"
```

`test_llm.py::test_streaming_sse_contract` asserts the role delta, `finish_reason: stop`, and `[DONE]` terminator.

## Agora never sees a tool_call

The tool loop runs synchronously inside `run_agent_turn()`. Only the final plain-text reply enters the streaming generator. **Do not** add `tool_calls` keys to streamed chunks — Agora does not process them and they would break the TTS pipeline.

## Replacing the mock

Edit `run_agent_turn()` in `server/src/llm.py`:

- Replace the keyword heuristic with a real model call that uses the OpenAI tool-call loop.
- Keep the function signature `(conn, messages) → str` if you want SQLite persistence; otherwise pass a different store.
- Preserve the SSE streaming contract above.
- Keep `llm.py` free of `agora_agent` imports (`test_llm_mount.py` enforces this via AST check).
- Validate `Authorization: Bearer` in `chat_completions` for production use.

## How the LLM is wired into the agent

In `Agent.start()` (`agent.py`):

```python
llm = CustomLLM(
    base_url=self.custom_llm_url,    # CUSTOM_LLM_URL, must be public
    api_key=self.custom_llm_api_key, # CUSTOM_LLM_API_KEY
    model=self.custom_llm_model,     # CUSTOM_LLM_MODEL, default "tool-mock"
    greeting_message=self.greeting,
    failure_message="Please wait a moment.",
    max_history=15,
    max_tokens=1024,
    temperature=0.7,
    top_p=0.95,
)
stt = DeepgramSTT(model="nova-3", language="en")
tts = MiniMaxTTS(model="speech_2_6_turbo", voice_id="English_captivating_female1")
agora_agent.with_stt(stt).with_llm(llm).with_tts(tts)
```

The `CustomLLM` vendor sets `vendor: "custom"` in the Agora wire config. Agora cloud then calls `base_url/chat/completions` directly for each turn.

## Related L1

- [02_architecture](../02_architecture.md) · [06_interfaces](../06_interfaces.md) · [07_gotchas](../07_gotchas.md)
