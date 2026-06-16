"""Unit tests for the alias state machine.

The patches in ``litellm_claude_aliases.patch`` are tested in
``test_patch.py``; this file covers only the pure translation logic.
"""

import pytest

from litellm_claude_aliases import aliases


@pytest.fixture(autouse=True)
def _reset_state():
    aliases.configure(None)
    yield
    aliases.configure(None)


def test_disabled_is_noop():
    body = {"model": "claude-sonnet-4-6-20251120"}
    aliases.translate_request_body(body)
    assert body["model"] == "claude-sonnet-4-6-20251120"


def test_translate_known_request_model():
    aliases.configure({
        "enabled": True,
        "request_mappings": {"claude-sonnet-4-6-20251120": "claude-3-5-sonnet"},
    })
    body = {"model": "claude-sonnet-4-6-20251120"}
    aliases.translate_request_body(body)
    assert body["model"] == "claude-3-5-sonnet"


def test_unknown_request_model_passes_through():
    aliases.configure({
        "enabled": True,
        "request_mappings": {"claude-sonnet-4-6-20251120": "claude-3-5-sonnet"},
    })
    body = {"model": "claude-3-5-sonnet"}
    aliases.translate_request_body(body)
    assert body["model"] == "claude-3-5-sonnet"


def test_remap_response_ids():
    aliases.configure({
        "enabled": True,
        "response_mappings": {"claude-3-5-sonnet": "claude-sonnet-4-6-20251120"},
    })
    input_list = [
        {"id": "claude-3-5-sonnet", "object": "model", "created": 1, "owned_by": "openai"},
        {"id": "some-other-model", "object": "model", "created": 1, "owned_by": "openai"},
    ]
    result = aliases.remap_model_list(input_list)
    assert result[0]["id"] == "claude-sonnet-4-6-20251120"
    assert result[1]["id"] == "some-other-model"
    # Original must not be mutated
    assert input_list[0]["id"] == "claude-3-5-sonnet"


def test_translate_does_not_crash_on_non_dict():
    aliases.configure({"enabled": True, "request_mappings": {"a": "b"}})
    aliases.translate_request_body("not a dict")
    aliases.translate_request_body(None)
    aliases.translate_request_body({"model": 123})  # non-string model


def test_reconfigure_disable_returns_to_noop():
    aliases.configure({
        "enabled": True,
        "request_mappings": {"a": "b"},
        "response_mappings": {"b": "a"},
    })
    assert aliases.is_enabled() is True
    aliases.configure({"enabled": False})
    assert aliases.is_enabled() is False
    body = {"model": "a"}
    aliases.translate_request_body(body)
    assert body["model"] == "a"
