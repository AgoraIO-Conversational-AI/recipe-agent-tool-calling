#!/bin/sh
# Supervise the bundled mock LLM (:8001) + the agent backend (:8000).
# POSIX sh: no `wait -n`; use a kill -0 liveness loop.

python /app/llm/src/custom_llm_server.py &
mock_pid=$!

python /app/server/src/server.py &
server_pid=$!

term() {
  kill "$mock_pid" "$server_pid" 2>/dev/null
}
trap term TERM INT

while kill -0 "$mock_pid" 2>/dev/null && kill -0 "$server_pid" 2>/dev/null; do
  sleep 1
done

term
exit 0
