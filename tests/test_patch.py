"""Tests for the monkey-patch layer.

We patch three LiteLLM functions:
  - ``litellm.proxy.proxy_server.model_list``
  - ``litellm.proxy.proxy_server.chat_completion``
  - ``litellm.proxy.anthropic_endpoints.endpoints.anthropic_response``

These tests replace the target functions on the module with fake callables,
run ``bootstrap()`` (which wraps them), then call the wrapped functions and
verify the wrappers both delegate AND apply alias translation.
"""

import pytest

from litellm_claude_aliases import aliases
from litellm_claude_aliases.patch import bootstrap


@pytest.fixture(autouse=True)
def _reset_aliases_and_patches():
    aliases.configure(None)
    yield
    aliases.configure(None)
    # Drop wrappers so other tests see the originals
    import litellm.proxy.proxy_server as ps
    import litellm.proxy.anthropic_endpoints.endpoints as ae

    if getattr(ps.model_list, "_lca_wrapped", False):
        ps.model_list = _original(ps.model_list)
    if getattr(ps.chat_completion, "_lca_wrapped", False):
        ps.chat_completion = _original(ps.chat_completion)
    if getattr(ae.anthropic_response, "_lca_wrapped", False):
        ae.anthropic_response = _original(ae.anthropic_response)


def _original(wrapped):
    while hasattr(wrapped, "__wrapped__"):
        wrapped = wrapped.__wrapped__
    return wrapped


def _make_fake_model_list(return_value):
    async def fake(*args, **kwargs):
        return return_value

    fake.__name__ = "model_list"
    return fake


def _make_fake_chat_completion(captured):
    async def fake(*args, **kwargs):
        captured.append(kwargs.get("data"))
        return {"ok": True}

    fake.__name__ = "chat_completion"
    return fake


def _make_fake_anthropic(captured):
    async def fake(*args, **kwargs):
        captured.append(kwargs.get("data"))
        return {"ok": True}

    fake.__name__ = "anthropic_response"
    return fake


@pytest.mark.asyncio
async def test_model_list_wraps_and_remaps():
    import litellm.proxy.proxy_server as ps

    original = _make_fake_model_list(
        {"data": [{"id": "claude-3-5-sonnet", "object": "model"}], "object": "list"}
    )
    ps.model_list = original
    aliases.configure({
        "enabled": True,
        "response_mappings": {"claude-3-5-sonnet": "claude-sonnet-4-6-20251120"},
    })

    bootstrap()
    result = await ps.model_list()

    assert result["data"][0]["id"] == "claude-sonnet-4-6-20251120"
    # Original must not be mutated
    assert result["data"][1] == {"object": "list"}


@pytest.mark.asyncio
async def test_model_list_noop_when_disabled():
    import litellm.proxy.proxy_server as ps

    original = _make_fake_model_list(
        {"data": [{"id": "claude-3-5-sonnet", "object": "model"}], "object": "list"}
    )
    ps.model_list = original

    bootstrap()  # enabled defaults to False

    result = await ps.model_list()
    assert result["data"][0]["id"] == "claude-3-5-sonnet"


@pytest.mark.asyncio
async def test_chat_completion_translates_model():
    import litellm.proxy.proxy_server as ps

    captured = []
    ps.chat_completion = _make_fake_chat_completion(captured)
    aliases.configure({
        "enabled": True,
        "request_mappings": {"claude-sonnet-4-6-20251120": "claude-3-5-sonnet"},
    })

    bootstrap()
    await ps.chat_completion(data={"model": "claude-sonnet-4-6-20251120"})

    # The wrapped function must have received the translated model
    assert captured[0]["model"] == "claude-3-5-sonnet"


@pytest.mark.asyncio
async def test_anthropic_response_translates_model():
    import litellm.proxy.anthropic_endpoints.endpoints as ae

    captured = []
    ae.anthropic_response = _make_fake_anthropic(captured)
    aliases.configure({
        "enabled": True,
        "request_mappings": {"claude-opus-4-8-20251120": "claude-3-5-opus"},
    })

    bootstrap()
    await ae.anthropic_response(data={"model": "claude-opus-4-8-20251120"})

    assert captured[0]["model"] == "claude-3-5-opus"


def test_bootstrap_is_idempotent():
    import litellm.proxy.proxy_server as ps
    import litellm.proxy.anthropic_endpoints.endpoints as ae

    ps.model_list = _make_fake_model_list({"data": [], "object": "list"})
    ps.chat_completion = _make_fake_chat_completion([])
    ae.anthropic_response = _make_fake_anthropic([])

    bootstrap()
    first_ml = ps.model_list
    first_cc = ps.chat_completion
    first_ar = ae.anthropic_response

    bootstrap()
    assert ps.model_list is first_ml
    assert ps.chat_completion is first_cc
    assert ae.anthropic_response is first_ar
