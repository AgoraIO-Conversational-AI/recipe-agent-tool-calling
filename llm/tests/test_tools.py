import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import custom_llm_server as srv  # noqa: E402


def setup_function():
    srv.MESSAGE_LOG.clear()


def _user(text):
    return srv.UserMessage(role="user", content=text)


def test_log_message_records_and_confirms():
    reply = srv.run_agent_turn([_user("log this: buy milk")])
    assert "buy milk" in srv.MESSAGE_LOG
    assert "buy milk" in reply


def test_non_tool_message_returns_guidance():
    reply = srv.run_agent_turn([_user("hello there")])
    assert srv.MESSAGE_LOG == []
    assert "log" in reply.lower()
